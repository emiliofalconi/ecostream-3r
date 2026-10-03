fn main() -> Result<(), Box<dyn std::error::Error>> {
    tonic_build::configure()
        .build_server(true)
        .build_client(true)
        .compile_protos(
            &[
                "proto/ecostream/v1/common.proto",
                "proto/ecostream/v1/auth.proto",
                "proto/ecostream/v1/matchmaking.proto",
                "proto/ecostream/v1/gameplay.proto",
            ],
            &["proto"],
        )?;
    Ok(())
}
