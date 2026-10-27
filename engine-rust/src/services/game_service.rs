use std::collections::HashMap;
use std::pin::Pin;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{broadcast, mpsc, Mutex};
use tokio_stream::{wrappers::ReceiverStream, Stream, StreamExt};
use tonic::{Request, Response, Status, Streaming};

use crate::proto::ecostream::v1::*;
use crate::proto::ecostream::v1::game_simulation_service_server::GameSimulationService;
use crate::simulation::GameRoomSimulation;

#[derive(Clone)]
pub struct RoomHandle {
    pub room_id: String,
    pub sim: Arc<Mutex<GameRoomSimulation>>,
    pub world_broadcast_tx: broadcast::Sender<ServerStreamMessage>,
    pub chat_broadcast_tx: broadcast::Sender<ChatMessage>,
}

pub struct GameServiceImpl {
    rooms: Arc<Mutex<HashMap<String, RoomHandle>>>,
}

impl GameServiceImpl {
    pub fn new() -> Self {
        Self {
            rooms: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    async fn get_or_create_room(&self, room_id: &str) -> RoomHandle {
        let mut rooms = self.rooms.lock().await;
        if let Some(handle) = rooms.get(room_id) {
            return handle.clone();
        }

        let sim = Arc::new(Mutex::new(GameRoomSimulation::new(room_id.to_string())));
        // Canales broadcast compartidos entre todos los clientes de la sala
        let (world_broadcast_tx, _) = broadcast::channel(256);
        let (chat_broadcast_tx, _) = broadcast::channel(128);

        let handle = RoomHandle {
            room_id: room_id.to_string(),
            sim: sim.clone(),
            world_broadcast_tx: world_broadcast_tx.clone(),
            chat_broadcast_tx,
        };

        rooms.insert(room_id.to_string(), handle.clone());

        // ----------------------------------------------------------------------
        // UN ÚNICO GAME LOOP CENTRAL A 20 Hz POR SALA (50ms por Tick)
        // Solución al bug de multi-spawn y sobrecarga de red
        // ----------------------------------------------------------------------
        let sim_loop = sim.clone();
        let bcast_tx = world_broadcast_tx.clone();
        let r_id = room_id.to_string();

        tokio::spawn(async move {
            println!("[ROOM ENGINE] Loop autoritativo central iniciado a 20 Hz para sala '{}'", r_id);
            let mut interval = tokio::time::interval(Duration::from_millis(50));
            interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);

            loop {
                interval.tick().await;

                let (world_state, match_end) = {
                    let mut r = sim_loop.lock().await;
                    r.update_tick()
                };

                // Si ocurrió un evento de fin de partida (Victoria o Derrota)
                if let Some(end_event) = match_end {
                    let end_msg = ServerStreamMessage {
                        server_tick: world_state.tick,
                        server_timestamp_unix_ms: chrono::Utc::now().timestamp_millis(),
                        payload: Some(server_stream_message::Payload::MatchEnd(end_event)),
                    };
                    let _ = bcast_tx.send(end_msg);

                    // Difundir estado final
                    let final_state_msg = ServerStreamMessage {
                        server_tick: world_state.tick,
                        server_timestamp_unix_ms: chrono::Utc::now().timestamp_millis(),
                        payload: Some(server_stream_message::Payload::WorldState(world_state)),
                    };
                    let _ = bcast_tx.send(final_state_msg);

                    println!("[ROOM ENGINE] Partida finalizada en sala '{}'. Deteniendo loop de simulación.", r_id);
                    break;
                }

                let tick_msg = ServerStreamMessage {
                    server_tick: world_state.tick,
                    server_timestamp_unix_ms: chrono::Utc::now().timestamp_millis(),
                    payload: Some(server_stream_message::Payload::WorldState(world_state)),
                };

                // Difundir a todos los clientes suscritos
                let _ = bcast_tx.send(tick_msg);
            }
        });

        handle
    }
}

#[tonic::async_trait]
impl GameSimulationService for GameServiceImpl {
    type StreamGameStream = Pin<Box<dyn Stream<Item = Result<ServerStreamMessage, Status>> + Send + 'static>>;
    type StreamChatStream = Pin<Box<dyn Stream<Item = Result<ChatMessage, Status>> + Send + 'static>>;

    /// Streaming Bidireccional HTTP/2 a 20 Ticks/segundo
    async fn stream_game(
        &self,
        request: Request<Streaming<ClientStreamMessage>>,
    ) -> Result<Response<Self::StreamGameStream>, Status> {
        let mut in_stream = request.into_inner();
        let (tx, rx) = mpsc::channel(128);

        // Esperar el primer mensaje para identificar la sala y jugador
        let first_msg = match in_stream.next().await {
            Some(Ok(msg)) => msg,
            _ => return Err(Status::invalid_argument("Mensaje inicial requerido")),
        };

        let room_id = first_msg.room_id.clone();
        let player_id = first_msg.player_id.clone();
        let room_handle = self.get_or_create_room(&room_id).await;

        // Registrar o reconectar jugador y emitir ticket de reconexión
        let reconnect_ticket = {
            let mut r = room_handle.sim.lock().await;
            r.upsert_player(player_id.clone(), format!("Player_{}", &player_id[..4.min(player_id.len())]), 4)
        };

        // Enviar Snapshot inicial con ticket de sesión
        let initial_state = {
            let r = room_handle.sim.lock().await;
            r.build_current_state()
        };

        let initial_snapshot = ServerStreamMessage {
            server_tick: initial_state.tick,
            server_timestamp_unix_ms: chrono::Utc::now().timestamp_millis(),
            payload: Some(server_stream_message::Payload::InitialSnapshot(GameWorldSnapshot {
                baseline_tick: initial_state.tick,
                room_id: room_id.clone(),
                reconnect_ticket,
                current_state: Some(initial_state),
                match_duration_seconds: 180,
            })),
        };

        let _ = tx.send(Ok(initial_snapshot)).await;

        // Tarea 1: Consumir acciones, pings y heartbeats del cliente
        let sim_action = room_handle.sim.clone();
        let p_id_actions = player_id.clone();
        let tx_pong = tx.clone();
        let r_id_actions = room_id.clone();
        tokio::spawn(async move {
            let mut stream = in_stream;
            while let Some(Ok(client_msg)) = stream.next().await {
                if let Some(payload) = client_msg.payload {
                    match payload {
                        client_stream_message::Payload::Action(action) => {
                            let mut r = sim_action.lock().await;
                            r.apply_action(&p_id_actions, action);
                        }
                        client_stream_message::Payload::Ping(ping) => {
                            let pong = ServerStreamMessage {
                                server_tick: 0,
                                server_timestamp_unix_ms: chrono::Utc::now().timestamp_millis(),
                                payload: Some(server_stream_message::Payload::Pong(PongMessage {
                                    echo_client_timestamp_ms: ping.client_timestamp_ms,
                                    server_tick: 0,
                                    server_timestamp_ms: chrono::Utc::now().timestamp_millis() as u64,
                                })),
                            };
                            let _ = tx_pong.send(Ok(pong)).await;
                        }
                        client_stream_message::Payload::Heartbeat(hb) => {
                            let _ = hb.timestamp_unix_ms;
                        }
                    }
                }
            }

            // Al cerrar el stream de entrada, marcar jugador como desconectado
            let mut r = sim_action.lock().await;
            r.disconnect_player(&p_id_actions);
            println!("[DISCONNECT] Stream de entrada cerrado para jugador '{}' en sala '{}'", p_id_actions, r_id_actions);
        });

        // Tarea 2: Suscribirse al broadcast central de la sala y enviar ticks al cliente
        let mut bcast_rx = room_handle.world_broadcast_tx.subscribe();
        let sim_disconnect = room_handle.sim.clone();
        let p_id_disconnect = player_id.clone();
        tokio::spawn(async move {
            loop {
                match bcast_rx.recv().await {
                    Ok(msg) => {
                        if tx.send(Ok(msg)).await.is_err() {
                            // Cliente desconectado
                            break;
                        }
                    }
                    Err(broadcast::error::RecvError::Lagged(skipped)) => {
                        // Optimización de red: si el cliente sufre lag, saltar ticks acumulados sin abortar stream
                        println!("[NETWORK LAG] Cliente '{}' se atrasó en {} ticks; resincronizando", p_id_disconnect, skipped);
                    }
                    Err(broadcast::error::RecvError::Closed) => {
                        break;
                    }
                }
            }

            let mut r = sim_disconnect.lock().await;
            r.disconnect_player(&p_id_disconnect);
        });

        let output_stream = ReceiverStream::new(rx);
        Ok(Response::new(Box::pin(output_stream) as Self::StreamGameStream))
    }

    /// Protocolo de Reconexión Transitoria (< 5s Grace Period) (agregado por Victor)
    async fn reconnect_session(
        &self,
        request: Request<ReconnectRequest>,
    ) -> Result<Response<ReconnectResponse>, Status> {
        let req = request.into_inner();
        let rooms = self.rooms.lock().await;

        if let Some(handle) = rooms.get(&req.room_id) {
            let mut r = handle.sim.lock().await;
            if let Some(valid_ticket) = r.session_tickets.get(&req.player_id).cloned() {
                if valid_ticket == req.reconnect_ticket {
                    if let Some(player) = r.players.get_mut(&req.player_id) {
                        player.is_connected = true;
                    }
                    let current_state = r.last_snapshot.clone().unwrap_or_else(|| r.build_current_state());
                    let snapshot = GameWorldSnapshot {
                        baseline_tick: r.tick,
                        room_id: req.room_id,
                        reconnect_ticket: valid_ticket,
                        current_state: Some(current_state),
                        match_duration_seconds: r.remaining_seconds as i64,
                    };
                    return Ok(Response::new(ReconnectResponse {
                        success: true,
                        message: "Reconexión exitosa. Estado reconciliado con motor de Rust.".to_string(),
                        snapshot: Some(snapshot),
                    }));
                }
            }
        }

        Ok(Response::new(ReconnectResponse {
            success: false,
            message: "Ticket de reconexión inválido o expirado".to_string(),
            snapshot: None,
        }))
    }

    async fn send_chat_message(
        &self,
        request: Request<ChatMessage>,
    ) -> Result<Response<ChatAcknowledge>, Status> {
        let msg = request.into_inner();
        let rooms = self.rooms.lock().await;

        if let Some(handle) = rooms.get(&msg.room_id) {
            // Difundir el mensaje a todos los suscriptores en la sala
            let _ = handle.chat_broadcast_tx.send(msg.clone());
        }

        Ok(Response::new(ChatAcknowledge {
            success: true,
            message_id: msg.message_id,
            timestamp_unix_ms: chrono::Utc::now().timestamp_millis(),
        }))
    }

    async fn stream_chat(
        &self,
        request: Request<StreamChatRequest>,
    ) -> Result<Response<Self::StreamChatStream>, Status> {
        let req = request.into_inner();
        let room_handle = self.get_or_create_room(&req.room_id).await;

        let (tx, rx) = mpsc::channel(64);
        let mut chat_rx = room_handle.chat_broadcast_tx.subscribe();

        tokio::spawn(async move {
            loop {
                match chat_rx.recv().await {
                    Ok(chat_msg) => {
                        if tx.send(Ok(chat_msg)).await.is_err() {
                            break;
                        }
                    }
                    Err(broadcast::error::RecvError::Lagged(_)) => {
                        // Continuar con mensajes recientes
                    }
                    Err(broadcast::error::RecvError::Closed) => {
                        break;
                    }
                }
            }
        });

        let output_stream = ReceiverStream::new(rx);
        Ok(Response::new(Box::pin(output_stream) as Self::StreamChatStream))
    }
}
