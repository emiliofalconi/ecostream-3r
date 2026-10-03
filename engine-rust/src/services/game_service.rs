use std::collections::HashMap;
use std::pin::Pin;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{mpsc, Mutex};
use tokio_stream::{wrappers::ReceiverStream, Stream, StreamExt};
use tonic::{Request, Response, Status, Streaming};

use crate::proto::ecostream::v1::*;
use crate::proto::ecostream::v1::game_simulation_service_server::GameSimulationService;
use crate::simulation::GameRoomSimulation;

pub struct GameServiceImpl {
    rooms: Arc<Mutex<HashMap<String, Arc<Mutex<GameRoomSimulation>>>>>,
}

impl GameServiceImpl {
    pub fn new() -> Self {
        Self {
            rooms: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    async fn get_or_create_room(&self, room_id: &str) -> Arc<Mutex<GameRoomSimulation>> {
        let mut rooms = self.rooms.lock().await;
        rooms
            .entry(room_id.to_string())
            .or_insert_with(|| Arc::new(Mutex::new(GameRoomSimulation::new(room_id.to_string()))))
            .clone()
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
        let room = self.get_or_create_room(&room_id).await;

        // Registrar jugador y emitir ticket de reconexión
        let reconnect_ticket = {
            let mut r = room.lock().await;
            r.upsert_player(player_id.clone(), format!("Player_{}", &player_id[..4.min(player_id.len())]), 4)
        };

        // Enviar Snapshot inicial con ticket de sesión
        let initial_state = {
            let mut r = room.lock().await;
            r.update_tick()
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

        // Tarea 1: Consumir acciones del cliente
        let room_action = room.clone();
        let p_id = player_id.clone();
        let tx_pong = tx.clone();
        tokio::spawn(async move {
            let mut stream = in_stream;
            while let Some(Ok(client_msg)) = stream.next().await {
                if let Some(payload) = client_msg.payload {
                    match payload {
                        client_stream_message::Payload::Action(action) => {
                            let mut r = room_action.lock().await;
                            r.apply_action(&p_id, action);
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
                        _ => {}
                    }
                }
            }
        });

        // Tarea 2: Bucle Autoritativo emitiendo GameWorldState a 20 Hz (50ms)
        let room_tick = room.clone();
        tokio::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_millis(50));
            loop {
                interval.tick().await;
                let world_state = {
                    let mut r = room_tick.lock().await;
                    r.update_tick()
                };

                let msg = ServerStreamMessage {
                    server_tick: world_state.tick,
                    server_timestamp_unix_ms: chrono::Utc::now().timestamp_millis(),
                    payload: Some(server_stream_message::Payload::WorldState(world_state)),
                };

                if tx.send(Ok(msg)).await.is_err() {
                    // Cliente desconectado
                    break;
                }
            }
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

        if let Some(room_arc) = rooms.get(&req.room_id) {
            let r = room_arc.lock().await;
            if let Some(valid_ticket) = r.session_tickets.get(&req.player_id) {
                if valid_ticket == &req.reconnect_ticket {
                    let snapshot = GameWorldSnapshot {
                        baseline_tick: r.tick,
                        room_id: req.room_id,
                        reconnect_ticket: valid_ticket.clone(),
                        current_state: r.last_snapshot.clone(),
                        match_duration_seconds: r.remaining_seconds as i64,
                    };
                    return Ok(Response::new(ReconnectResponse {
                        success: true,
                        message: "Reconexion exitosa. Estado reconciliado.".to_string(),
                        snapshot: Some(snapshot),
                    }));
                }
            }
        }

        Ok(Response::new(ReconnectResponse {
            success: false,
            message: "Ticket de reconexion invalido o expirado".to_string(),
            snapshot: None,
        }))
    }

    async fn send_chat_message(
        &self,
        request: Request<ChatMessage>,
    ) -> Result<Response<ChatAcknowledge>, Status> {
        let msg = request.into_inner();
        Ok(Response::new(ChatAcknowledge {
            success: true,
            message_id: msg.message_id,
            timestamp_unix_ms: chrono::Utc::now().timestamp_millis(),
        }))
    }

    async fn stream_chat(
        &self,
        _request: Request<StreamChatRequest>,
    ) -> Result<Response<Self::StreamChatStream>, Status> {
        let (_tx, rx) = mpsc::channel(16);
        let output_stream = ReceiverStream::new(rx);
        Ok(Response::new(Box::pin(output_stream) as Self::StreamChatStream))
    }
}
