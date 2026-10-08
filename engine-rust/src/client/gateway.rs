use tracing::{info, warn};

use crate::proto::ecostream::v1::internal_coordinator_service_client::InternalCoordinatorServiceClient;
use crate::proto::ecostream::v1::{MatchEndEvent, NotifyMatchFinishedRequest};

pub async fn notify_gateway_match_end(gateway_url: &str, room_id: &str, match_end: MatchEndEvent) {
    info!(
        "[GATEWAY-CLIENT] Notificando fin de partida para sala {} a Gateway en {}",
        room_id, gateway_url
    );

    match InternalCoordinatorServiceClient::connect(gateway_url.to_string()).await {
        Ok(mut client) => {
            let req = tonic::Request::new(NotifyMatchFinishedRequest {
                room_id: room_id.to_string(),
                final_state: Some(match_end),
            });

            match client.notify_match_finished(req).await {
                Ok(resp) => {
                    info!(
                        "[GATEWAY-CLIENT] Notificación exitosa recibida por Gateway: {:?}",
                        resp.into_inner().message
                    );
                }
                Err(status) => {
                    warn!(
                        "[GATEWAY-CLIENT] Gateway respondió con error gRPC: {} ({})",
                        status.message(),
                        status.code()
                    );
                }
            }
        }
        Err(e) => {
            warn!(
                "[GATEWAY-CLIENT] No se pudo conectar a Gateway Go en {}: {} (reintento omitido)",
                gateway_url, e
            );
        }
    }
}
