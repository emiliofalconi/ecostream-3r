#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Compiling Protobuf definitions for Go Gateway..."
mkdir -p "${ROOT_DIR}/gateway-go/proto/v1"

protoc --proto_path="${ROOT_DIR}/proto" \
  --go_out="${ROOT_DIR}/gateway-go/proto/v1" --go_opt=module=github.com/Makmadon/ecostream-3r/gateway-go/proto/v1 \
  --go-grpc_out="${ROOT_DIR}/gateway-go/proto/v1" --go-grpc_opt=module=github.com/Makmadon/ecostream-3r/gateway-go/proto/v1 \
  "${ROOT_DIR}/proto/ecostream/v1/"*.proto

echo "Synchronizing Protobuf files to engine-rust/proto..."
mkdir -p "${ROOT_DIR}/engine-rust/proto/ecostream/v1"
cp -r "${ROOT_DIR}/proto/ecostream/v1/"*.proto "${ROOT_DIR}/engine-rust/proto/ecostream/v1/"

echo "Protobuf synchronization and generation completed successfully."
