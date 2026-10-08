use std::sync::Arc;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use tokio::sync::{broadcast, mpsc, RwLock};
use tracing::info;

use super::snapshot::*;
use super::world::GameWorld;
use crate::proto::ecostream::v1::player_action::ActionType;
use crate::proto::ecostream::v1::server_stream_message::Payload;
use crate::proto::ecostream::v1::*;

#[derive(Debug)]
pub enum RoomActionCommand {
    PlayerAction {
        player_id: String,
        action: PlayerAction,
    },
    PlayerDisconnect {
        player_id: String,
    },
    PlayerConnect {
        player_id: String,
        username: String,
        role: i32,
    },
}

#[derive(Clone)]
#[allow(dead_code)]
pub struct RoomHandle {
    pub room_id: String,
    pub world: Arc<RwLock<GameWorld>>,
    pub action_tx: mpsc::Sender<RoomActionCommand>,
    pub broadcast_tx: broadcast::Sender<ServerStreamMessage>,
}

impl RoomHandle {
    pub fn new(room_id: String, difficulty: u32, grace_seconds: u64, gateway_url: String) -> Self {
        let world = Arc::new(RwLock::new(GameWorld::new(room_id.clone(), difficulty)));
        let (action_tx, mut action_rx) = mpsc::channel::<RoomActionCommand>(500);
        let (broadcast_tx, _) = broadcast::channel::<ServerStreamMessage>(100);

        let world_clone = Arc::clone(&world);
        let broadcast_tx_clone = broadcast_tx.clone();
        let room_id_clone = room_id.clone();

        tokio::spawn(async move {
            info!("[ROOM {}] Iniciando Game Loop autoritativo a 20 Hz...", room_id_clone);
            let mut ticker = tokio::time::interval(Duration::from_millis(50));
            ticker.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);

            let dt = 0.05; // 50ms per tick

            loop {
                ticker.tick().await;

                // 1. Drenar y procesar acciones pendientes
                while let Ok(cmd) = action_rx.try_recv() {
                    let mut w = world_clone.write().await;
                    match cmd {
                        RoomActionCommand::PlayerConnect { player_id, username, role } => {
                            w.add_or_update_player(player_id, username, role);
                        }
                        RoomActionCommand::PlayerDisconnect { player_id } => {
                            w.mark_player_disconnected(&player_id);
                        }
                        RoomActionCommand::PlayerAction { player_id, action } => {
                            if let Some(action_type) = action.action_type {
                                match action_type {
                                    ActionType::Move(move_act) => {
                                        w.apply_move(&player_id, move_act.direction_x, move_act.direction_y, dt);
                                    }
                                    ActionType::RepairPipe(repair_act) => {
                                        w.apply_repair_pipe(&player_id, repair_act.pipe_id, dt);
                                    }
                                    ActionType::DivertValve(divert_act) => {
                                        w.apply_divert_valve(&player_id, divert_act.valve_id, divert_act.destination);
                                    }
                                    ActionType::OperateRecycle(recycle_act) => {
                                        w.apply_recycle_op(&player_id, recycle_act.plant_id, recycle_act.operation);
                                    }
                                    _ => {}
                                }
                            }
                        }
                    }
                }

                // 2. Ejecutar simulación de física y métricas 3R
                let mut w = world_clone.write().await;
                w.update(dt);

                // 3. Chequear expiración de periodo de gracia (10s) para reconexiones
                let now = Instant::now();
                for player in w.players.values_mut() {
                    if !player.is_connected {
                        if let Some(disc_at) = player.disconnected_at {
                            if now.duration_since(disc_at).as_secs() > grace_seconds {
                                // Expiró gracia: sigue desconectado pero su puesto queda marcado
                            }
                        }
                    }
                }

                let tick = w.tick;
                let is_finished = w.is_finished;

                // 4. Emitir estado del mundo a todos los clientes suscritos (20 Hz)
                let now_ms = SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_millis() as i64;

                let msg = ServerStreamMessage {
                    server_tick: tick,
                    server_timestamp_unix_ms: now_ms,
                    payload: Some(Payload::WorldState(world_to_proto_state(&w))),
                };

                let _ = broadcast_tx_clone.send(msg);

                // 5. Manejo de fin de partida
                if is_finished {
                    info!("[ROOM {}] Partida finalizada! Razón: {}", room_id_clone, w.finish_reason);
                    let match_end_event = world_to_proto_match_end(&w);

                    let end_msg = ServerStreamMessage {
                        server_tick: tick,
                        server_timestamp_unix_ms: now_ms,
                        payload: Some(Payload::MatchEnd(match_end_event.clone())),
                    };
                    let _ = broadcast_tx_clone.send(end_msg);

                    // Notificar asíncronamente al Gateway Go
                    let r_id = room_id_clone.clone();
                    let g_url = gateway_url.clone();
                    tokio::spawn(async move {
                        crate::client::gateway::notify_gateway_match_end(&g_url, &r_id, match_end_event).await;
                    });

                    break;
                }
            }
            info!("[ROOM {}] Loop de juego terminado limpiamente.", room_id_clone);
        });

        Self {
            room_id,
            world,
            action_tx,
            broadcast_tx,
        }
    }
}
