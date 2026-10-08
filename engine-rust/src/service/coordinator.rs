use tonic::{Request, Response, Status};
use tracing::info;

use crate::game::r#loop::RoomActionCommand;
use crate::game::RoomManager;
use crate::proto::ecostream::v1::internal_coordinator_service_server::InternalCoordinatorService;
use crate::proto::ecostream::v1::*;

pub struct CoordinatorService {
    room_manager: RoomManager,
    simulation_endpoint: String,
}

impl CoordinatorService {
    pub fn new(room_manager: RoomManager, simulation_endpoint: String) -> Self {
        Self {
            room_manager,
            simulation_endpoint,
        }
    }
}

#[tonic::async_trait]
impl InternalCoordinatorService for CoordinatorService {
    async fn provision_room(
        &self,
        request: Request<ProvisionRoomRequest>,
    ) -> Result<Response<ProvisionRoomResponse>, Status> {
        let req = request.into_inner();
        info!(
            "[COORDINATOR] Solicitud de aprovisionamiento para sala {} (dificultad: {})",
            req.room_id, req.difficulty_level
        );

        let handle = self.room_manager.get_or_create_room(&req.room_id, req.difficulty_level).await;

        for player in req.players {
            let _ = handle.action_tx.send(RoomActionCommand::PlayerConnect {
                player_id: player.user_id,
                username: player.username,
                role: player.selected_role,
            }).await;
        }

        Ok(Response::new(ProvisionRoomResponse {
            success: true,
            message: "Instancia de simulación aprovisionada con éxito en Rust".to_string(),
            simulation_endpoint: self.simulation_endpoint.clone(),
        }))
    }

    async fn notify_match_finished(
        &self,
        _request: Request<NotifyMatchFinishedRequest>,
    ) -> Result<Response<NotifyMatchFinishedResponse>, Status> {
        Ok(Response::new(NotifyMatchFinishedResponse {
            acknowledged: true,
            message: "Reconocido por Rust".to_string(),
        }))
    }
}
