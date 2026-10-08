use std::path::Path;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let proto_root = if Path::new("../proto").exists() {
        "../proto"
    } else {
        "proto"
    };

    let proto_files = [
        format!("{}/ecostream/v1/common.proto", proto_root),
        format!("{}/ecostream/v1/auth.proto", proto_root),
        format!("{}/ecostream/v1/matchmaking.proto", proto_root),
        format!("{}/ecostream/v1/gameplay.proto", proto_root),
        format!("{}/ecostream/v1/internal.proto", proto_root),
    ];

    for file in &proto_files {
        println!("cargo:rerun-if-changed={}", file);
    }

    tonic_build::configure()
        .build_server(true)
        .build_client(true)
        .compile_protos(&proto_files, &[proto_root])?;

    Ok(())
}
