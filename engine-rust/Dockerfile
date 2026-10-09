# Build stage
FROM rust:alpine AS builder

RUN apk add --no-cache musl-dev protobuf-dev protoc git

WORKDIR /app

# Copiar definiciones proto y código fuente
COPY Cargo.toml Cargo.lock* build.rs ./
COPY proto ./proto/
COPY src ./src/

RUN cargo build --release

# Final runtime stage
FROM alpine:3.20

WORKDIR /app

RUN apk add --no-cache ca-certificates tzdata

COPY --from=builder /app/target/release/engine-rust /app/engine-rust

EXPOSE 50052

ENTRYPOINT ["/app/engine-rust"]
