use std::net::SocketAddr;
use std::sync::Arc;
use tonic::transport::Server;
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

use engine_rust::auth::ticket::TicketVerifier;
use engine_rust::config::Config;
use engine_rust::game::RoomManager;
use engine_rust::proto::ecostream::v1::game_simulation_service_server::GameSimulationServiceServer;
use engine_rust::proto::ecostream::v1::internal_coordinator_service_server::InternalCoordinatorServiceServer;
use engine_rust::service::chat::ChatManager;
use engine_rust::service::coordinator::CoordinatorService;
use engine_rust::service::simulation::SimulationService;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let subscriber = FmtSubscriber::builder()
        .with_max_level(Level::INFO)
        .finish();
    tracing::subscriber::set_global_default(subscriber)
        .expect("Fallo al inicializar logger");

    info!("==================================================");
    info!(" EcoStream-3R: Motor de Simulación Autoritativo");
    info!(" Tiempo Real Tokio / Tonic (20 Hz - 50ms ticks)");
    info!(" Cátedra: Computación en la Nube (UCAB)");
    info!("==================================================");

    let cfg = Config::from_env();
    info!("Configuración cargada: Puerto={}, Ticks={}Hz, Gracia={}s",
        cfg.simulation_port, cfg.tick_rate_hz, cfg.reconnect_grace_seconds
    );

    let addr: SocketAddr = format!("0.0.0.0:{}", cfg.simulation_port).parse()?;

    let room_manager = RoomManager::new(cfg.reconnect_grace_seconds, cfg.gateway_internal_url.clone());
    let ticket_verifier = Arc::new(TicketVerifier::new(&cfg.hmac_secret));
    let chat_manager = ChatManager::new();

    let sim_service = SimulationService::new(
        room_manager.clone(),
        ticket_verifier,
        chat_manager,
    );

    let room_manager_shutdown = room_manager.clone();
    let coord_service = CoordinatorService::new(
        room_manager,
        format!("localhost:{}", cfg.simulation_port),
    );

    info!("[SERVER] Servidor gRPC de Simulación escuchando en {}", addr);

    Server::builder()
        .accept_http1(true)
        .add_service(GameSimulationServiceServer::new(sim_service))
        .add_service(InternalCoordinatorServiceServer::new(coord_service))
        .serve_with_shutdown(addr, async move {
            tokio::signal::ctrl_c()
                .await
                .expect("Fallo al capturar señal CTRL+C");
            info!("[SERVER] Señal de terminación recibida. Vaciando partidas activas antes de apagar...");
            room_manager_shutdown.flush_all_active_rooms("SERVER_SHUTDOWN").await;
            info!("[SERVER] Vaciado completado. Apagando servidor gRPC...");
        })
        .await?;

    info!("[SERVER] Motor de Simulación finalizado limpiamente.");
    Ok(())
}
