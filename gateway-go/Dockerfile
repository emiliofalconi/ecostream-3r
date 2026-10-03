# Etapa 1: Compilación en Go 1.22
FROM golang:1.22-alpine AS builder

WORKDIR /app

# Instalar certificados y git
RUN apk add --no-cache git ca-certificates

# Copiar todo el código del gateway
COPY . .

# Descargar módulos y generar go.sum completo
RUN go mod tidy

# Compilar binario estático optimizado
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /gateway-go main.go

# Etapa 2: Imagen Final Ultraligera
FROM alpine:3.20

WORKDIR /app

RUN apk add --no-cache ca-certificates curl

# Copiar binario compilado
COPY --from=builder /gateway-go /app/gateway-go

# Copiar documentación swagger
COPY docs/swagger/openapi.json /app/docs/swagger/openapi.json

EXPOSE 8080 50051

ENTRYPOINT ["/app/gateway-go"]
