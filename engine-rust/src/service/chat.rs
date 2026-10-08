use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::{broadcast, RwLock};

use crate::proto::ecostream::v1::ChatMessage;

#[derive(Clone)]
pub struct ChatManager {
    channels: Arc<RwLock<HashMap<String, broadcast::Sender<ChatMessage>>>>,
}

impl ChatManager {
    pub fn new() -> Self {
        Self {
            channels: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub async fn get_or_create_channel(&self, room_id: &str) -> broadcast::Sender<ChatMessage> {
        let mut map = self.channels.write().await;
        if let Some(tx) = map.get(room_id) {
            tx.clone()
        } else {
            let (tx, _) = broadcast::channel(100);
            map.insert(room_id.to_string(), tx.clone());
            tx
        }
    }
}
