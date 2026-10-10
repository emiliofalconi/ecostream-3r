pub mod entities;
pub mod r#loop;
pub mod snapshot;
pub mod world;

use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

use self::r#loop::RoomHandle;

#[derive(Clone)]
pub struct RoomManager {
    rooms: Arc<RwLock<HashMap<String, RoomHandle>>>,
    grace_seconds: u64,
    gateway_url: String,
}

impl RoomManager {
    pub fn new(grace_seconds: u64, gateway_url: String) -> Self {
        Self {
            rooms: Arc::new(RwLock::new(HashMap::new())),
            grace_seconds,
            gateway_url,
        }
    }

    pub async fn get_or_create_room(&self, room_id: &str, difficulty: u32) -> RoomHandle {
        let mut rooms = self.rooms.write().await;
        if let Some(handle) = rooms.get(room_id) {
            handle.clone()
        } else {
            let handle = RoomHandle::new(
                room_id.to_string(),
                difficulty,
                self.grace_seconds,
                self.gateway_url.clone(),
            );
            rooms.insert(room_id.to_string(), handle.clone());
            handle
        }
    }

    pub async fn get_room(&self, room_id: &str) -> Option<RoomHandle> {
        let rooms = self.rooms.read().await;
        rooms.get(room_id).cloned()
    }

    /// Vaciado de emergencia ante apagado ordenado del servidor (SIGINT/SIGTERM)
    pub async fn flush_all_active_rooms(&self, reason: &str) {
        let rooms = self.rooms.read().await;
        for (room_id, handle) in rooms.iter() {
            let mut w = handle.world.write().await;
            if !w.is_finished {
                w.is_finished = true;
                w.finish_reason = reason.to_string();
                let match_end = snapshot::world_to_proto_match_end(&w);
                tracing::info!(
                    "[ROOM {}] Apagado ordenado detectado. Vaciando métricas acumuladas a Gateway ({reason})...",
                    room_id
                );
                crate::client::gateway::notify_gateway_match_end(
                    &self.gateway_url,
                    room_id,
                    match_end,
                ).await;
            }
        }
    }
}
