use std::pin::Pin;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use tokio_stream::wrappers::{BroadcastStream, ReceiverStream};
use tokio_stream::{Stream, StreamExt};
use tonic::{Request, Response, Status, Streaming};
use tracing::{info, warn};

use crate::auth::ticket::TicketVerifier;
use crate::game::r#loop::RoomActionCommand;
use crate::game::snapshot::*;
use crate::game::RoomManager;
use crate::proto::ecostream::v1::client_stream_message::Payload as ClientPayload;
use crate::proto::ecostream::v1::game_simulation_service_server::GameSimulationService;
use crate::proto::ecostream::v1::server_stream_message::Payload as ServerPayload;
use crate::proto::ecostream::v1::*;
use crate::service::chat::ChatManager;

pub struct SimulationService {
    room_manager: RoomManager,
    ticket_verifier: Arc<TicketVerifier>,
    chat_manager: ChatManager,
}

impl SimulationService {
    pub fn new(
        room_manager: RoomManager,
        ticket_verifier: Arc<TicketVerifier>,
        chat_manager: ChatManager,
    ) -> Self {
        Self {
            room_manager,
            ticket_verifier,
            chat_manager,
        }
    }
}

#[tonic::async_trait]
impl GameSimulationService for SimulationService {
    type StreamGameStream = Pin<Box<dyn Stream<Item = Result<ServerStreamMessage, Status>> + Send + 'static>>;

    async fn stream_game(
        &self,
        request: Request<Streaming<ClientStreamMessage>>,
    ) -> Result<Response<Self::StreamGameStream>, Status> {
        let mut in_stream = request.into_inner();
        let (out_tx, out_rx) = tokio::sync::mpsc::channel::<Result<ServerStreamMessage, Status>>(128);

        let room_mgr = self.room_manager.clone();
        let verifier = Arc::clone(&self.ticket_verifier);

        tokio::spawn(async move {
            // 1. Handshake inicial: El primer mensaje debe contener room_ticket válido
            let first_msg = match in_stream.next().await {
                Some(Ok(msg)) => msg,
                Some(Err(e)) => {
                    let _ = out_tx.send(Err(Status::internal(e.to_string()))).await;
                    return;
                }
                None => {
                    let _ = out_tx.send(Err(Status::invalid_argument("Stream cerrado antes del handshake"))).await;
                    return;
                }
            };

            let ticket = first_msg.room_ticket;
            if ticket.is_empty() {
                let _ = out_tx.send(Err(Status::unauthenticated("RoomTicket requerido en handshake"))).await;
                return;
            }

            let claims = match verifier.verify(&ticket) {
                Ok(c) => c,
                Err(err) => {
                    warn!("[AUTH] Rechazada conexión con ticket inválido: {}", err);
                    let _ = out_tx.send(Err(Status::unauthenticated(format!("Ticket inválido: {}", err)))).await;
                    return;
                }
            };

            let room_id = claims.room_id.clone();
            let player_id = claims.user_id.clone();
            let username = claims.username.clone();
            let role = claims.role;

            info!("[STREAM] Conexión autenticada para jugador {} ({}) en sala {}", username, player_id, room_id);

            let room_handle = room_mgr.get_or_create_room(&room_id, 1).await;

            // Registrar conexión del jugador en el mundo
            let _ = room_handle.action_tx.send(RoomActionCommand::PlayerConnect {
                player_id: player_id.clone(),
                username: username.clone(),
                role,
            }).await;

            // 2. Enviar Snapshot Inicial completo
            {
                let w = room_handle.world.read().await;
                let snapshot = world_to_proto_snapshot(&w, ticket.clone());
                let initial_msg = ServerStreamMessage {
                    server_tick: w.tick,
                    server_timestamp_unix_ms: SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_millis() as i64,
                    payload: Some(ServerPayload::InitialSnapshot(snapshot)),
                };
                if out_tx.send(Ok(initial_msg)).await.is_err() {
                    return;
                }
            }

            // Si el primer mensaje traía payload de acción o ping, procesarlo
            if let Some(payload) = first_msg.payload {
                match payload {
                    ClientPayload::Action(action) => {
                        let _ = room_handle.action_tx.send(RoomActionCommand::PlayerAction {
                            player_id: player_id.clone(),
                            action,
                        }).await;
                    }
                    ClientPayload::Ping(ping) => {
                        let now_ms = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_millis() as u64;
                        let pong_msg = ServerStreamMessage {
                            server_tick: 0,
                            server_timestamp_unix_ms: now_ms as i64,
                            payload: Some(ServerPayload::Pong(PongMessage {
                                echo_client_timestamp_ms: ping.client_timestamp_ms,
                                server_tick: 0,
                                server_timestamp_ms: now_ms,
                            })),
                        };
                        let _ = out_tx.send(Ok(pong_msg)).await;
                    }
                    _ => {}
                }
            }

            // 3. Suscripción a los ticks del servidor (20 Hz)
            let mut broadcast_rx = BroadcastStream::new(room_handle.broadcast_tx.subscribe());

            loop {
                tokio::select! {
                    // Mensajes entrantes del cliente
                    client_msg_opt = in_stream.next() => {
                        match client_msg_opt {
                            Some(Ok(client_msg)) => {
                                if let Some(payload) = client_msg.payload {
                                    match payload {
                                        ClientPayload::Action(act) => {
                                            let _ = room_handle.action_tx.send(RoomActionCommand::PlayerAction {
                                                player_id: player_id.clone(),
                                                action: act,
                                            }).await;
                                        }
                                        ClientPayload::Ping(ping) => {
                                            let tick = room_handle.world.read().await.tick;
                                            let now_ms = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_millis() as u64;
                                            let pong_msg = ServerStreamMessage {
                                                server_tick: tick,
                                                server_timestamp_unix_ms: now_ms as i64,
                                                payload: Some(ServerPayload::Pong(PongMessage {
                                                    echo_client_timestamp_ms: ping.client_timestamp_ms,
                                                    server_tick: tick,
                                                    server_timestamp_ms: now_ms,
                                                })),
                                            };
                                            if out_tx.send(Ok(pong_msg)).await.is_err() {
                                                break;
                                            }
                                        }
                                        ClientPayload::Heartbeat(_) => {}
                                    }
                                }
                            }
                            Some(Err(e)) => {
                                warn!("[STREAM] Error en stream de cliente {}: {}", player_id, e);
                                break;
                            }
                            None => {
                                info!("[STREAM] Cliente {} cerró stream.", player_id);
                                break;
                            }
                        }
                    }

                    // Mensajes salientes del mundo (20 Hz WorldState)
                    server_msg_res = broadcast_rx.next() => {
                        match server_msg_res {
                            Some(Ok(server_msg)) => {
                                if out_tx.send(Ok(server_msg)).await.is_err() {
                                    break;
                                }
                            }
                            Some(Err(_)) => {
                                // Lag en broadcast, saltar tick
                                continue;
                            }
                            None => {
                                break;
                            }
                        }
                    }
                }
            }

            // Cliente desconectado: marcar desconexión para periodo de gracia
            info!("[STREAM] Jugador {} desconectado. Iniciando periodo de gracia (10s)...", player_id);
            let _ = room_handle.action_tx.send(RoomActionCommand::PlayerDisconnect {
                player_id: player_id.clone(),
            }).await;
        });

        let output_stream = ReceiverStream::new(out_rx);
        Ok(Response::new(Box::pin(output_stream) as Self::StreamGameStream))
    }

    async fn reconnect_session(
        &self,
        request: Request<ReconnectRequest>,
    ) -> Result<Response<ReconnectResponse>, Status> {
        let req = request.into_inner();

        let claims = self.ticket_verifier.verify(&req.reconnect_ticket)
            .map_err(|e| Status::unauthenticated(format!("Ticket de reconexión inválido: {}", e)))?;

        let room_handle = match self.room_manager.get_room(&req.room_id).await {
            Some(h) => h,
            None => {
                return Ok(Response::new(ReconnectResponse {
                    success: false,
                    message: "La sala solicitada ya no existe o finalizó".to_string(),
                    snapshot: None,
                }));
            }
        };

        let w = room_handle.world.read().await;
        if let Some(player) = w.players.get(&req.player_id) {
            if let Some(disc_at) = player.disconnected_at {
                if disc_at.elapsed().as_secs() > 10 {
                    return Ok(Response::new(ReconnectResponse {
                        success: false,
                        message: "El periodo de gracia de reconexión (10s) ha expirado".to_string(),
                        snapshot: None,
                    }));
                }
            }
        }

        let snapshot = world_to_proto_snapshot(&w, req.reconnect_ticket);

        // Reactivar jugador
        let _ = room_handle.action_tx.send(RoomActionCommand::PlayerConnect {
            player_id: req.player_id,
            username: claims.username,
            role: claims.role,
        }).await;

        Ok(Response::new(ReconnectResponse {
            success: true,
            message: "Reconexión exitosa dentro del periodo de gracia".to_string(),
            snapshot: Some(snapshot),
        }))
    }

    async fn send_chat_message(
        &self,
        request: Request<ChatMessage>,
    ) -> Result<Response<ChatAcknowledge>, Status> {
        let msg = request.into_inner();
        let ch = self.chat_manager.get_or_create_channel(&msg.room_id).await;

        let msg_id = msg.message_id.clone();
        let now_ms = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_millis() as i64;

        let _ = ch.send(msg);

        Ok(Response::new(ChatAcknowledge {
            success: true,
            message_id: msg_id,
            timestamp_unix_ms: now_ms,
        }))
    }

    type StreamChatStream = Pin<Box<dyn Stream<Item = Result<ChatMessage, Status>> + Send + 'static>>;

    async fn stream_chat(
        &self,
        request: Request<StreamChatRequest>,
    ) -> Result<Response<Self::StreamChatStream>, Status> {
        let req = request.into_inner();
        let ch = self.chat_manager.get_or_create_channel(&req.room_id).await;
        let rx = ch.subscribe();

        let stream = BroadcastStream::new(rx).filter_map(|res| match res {
            Ok(msg) => Some(Ok(msg)),
            Err(_) => None,
        });

        Ok(Response::new(Box::pin(stream) as Self::StreamChatStream))
    }
}
