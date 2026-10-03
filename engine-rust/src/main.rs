use std::net::SocketAddr;
use tonic::transport::Server;

mod proto;
mod simulation;
mod services;

use proto::ecostream::v1::game_simulation_service_server::GameSimulationServiceServer;
use services::GameServiceImpl;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let port = std::env::var("SIMULATION_GRPC_PORT").unwrap_or_else(|_| "50052".to_string());
    let addr: SocketAddr = format!("0.0.0.0:{}", port).parse()?;

    let game_service = GameServiceImpl::new();

    println!("=============================================================");
    println!("🦀 ECOSTREAM 3R - DATA PLANE & SIMULATION ENGINE (Rust Tokio)");
    println!("=============================================================");
    println!("[RUST ENGINE] Servidor gRPC Tonic escuchando en {}", addr);
    println!("[RUST ENGINE] Game Loop autoritativo configurado a 20 Hz (50 ms/tick)");
    println!("[RUST ENGINE] Soporte de reconexión rápida con Grace Period (< 5s) activo");

    Server::builder()
        .add_service(GameSimulationServiceServer::new(game_service))
        .serve(addr)
        .await?;

    Ok(())
}
