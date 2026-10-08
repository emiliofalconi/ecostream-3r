# Build stage
FROM golang:1.23-alpine AS builder

WORKDIR /app

RUN apk add --no-cache git

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /app/gateway-bin ./cmd/server

# Final lightweight stage
FROM alpine:3.20

WORKDIR /app

RUN apk add --no-cache ca-certificates tzdata wget

COPY --from=builder /app/gateway-bin /app/gateway-bin

EXPOSE 8080 50051

ENTRYPOINT ["/app/gateway-bin"]
