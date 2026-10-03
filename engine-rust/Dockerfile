# Etapa 1: Compilación con Rust más reciente en Alpine
FROM rust:alpine AS builder

WORKDIR /app

# Instalar dependencias de compilación para tonic/protoc
RUN apk add --no-cache musl-dev protobuf-dev

# Copiar todo el código y protos
COPY . .

# Compilar binario estático optimizado en modo release
RUN cargo build --release

# Etapa 2: Imagen Final Ultraligera
FROM alpine:3.20

WORKDIR /app

RUN apk add --no-cache ca-certificates

# Copiar binario compilado
COPY --from=builder /app/target/release/engine-rust /app/engine-rust

EXPOSE 50052

ENTRYPOINT ["/app/engine-rust"]
