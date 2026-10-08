package main

import (
	"context"
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/health"
	healthpb "google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/reflection"

	"github.com/Makmadon/ecostream-3r/gateway-go/config"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/auth"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/coordinator"
	internalhttp "github.com/Makmadon/ecostream-3r/gateway-go/internal/http"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/matchmaking"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/storage"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/workerpool"
	ecostreamv1 "github.com/Makmadon/ecostream-3r/gateway-go/proto/v1"
)

func main() {
	log.Println("==================================================")
	log.Println(" EcoStream-3R: API Gateway & Matchmaking Service")
	log.Println(" Cátedra: Computación en la Nube (UCAB)")
	log.Println("==================================================")

	// 1. Cargar Configuración Centralizada
	cfg := config.LoadConfig()

	// 2. Conectar a PostgreSQL
	db, err := storage.NewPostgresDB(cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("[FATAL] Fallo al inicializar PostgreSQL: %v", err)
	}
	defer db.Close()

	// 3. Conectar a Redis (con soporte de degradación suave)
	redisClient, err := storage.NewRedisClient(cfg.RedisURL)
	if err != nil {
		log.Printf("[WARN] Error al configurar cliente Redis: %v", err)
	}
	defer redisClient.Close()

	// 4. Inicializar Worker Pool Asíncrono de Auditoría
	pool := workerpool.NewWorkerPool(db.DB, cfg.WorkerPoolCapacity, cfg.WorkerCount)

	// 5. Gestores Criptográficos
	jwtManager := auth.NewJWTManager(cfg.JWTSecret, cfg.JWTExpirationDuration)
	ticketManager := auth.NewTicketManager(cfg.HMACSecret, 60*time.Second)

	// 6. Servicios de Dominio
	authService := auth.NewService(db, jwtManager, pool)
	matchRepo := matchmaking.NewRepository(db)
	matchService := matchmaking.NewService(matchRepo, redisClient, ticketManager, pool, cfg.SimulationEngineURL)

	// 7. Handlers gRPC
	authGRPCHandler := auth.NewGRPCHandler(authService)
	matchGRPCHandler := matchmaking.NewGRPCHandler(matchService, jwtManager)
	coordGRPCHandler := coordinator.NewHandler(db, redisClient, pool)

	// 8. Configurar Servidor gRPC
	grpcServer := grpc.NewServer()
	ecostreamv1.RegisterAuthServiceServer(grpcServer, authGRPCHandler)
	ecostreamv1.RegisterMatchmakingServiceServer(grpcServer, matchGRPCHandler)
	ecostreamv1.RegisterInternalCoordinatorServiceServer(grpcServer, coordGRPCHandler)

	// Registrar gRPC Health Checking Protocol
	healthServer := health.NewServer()
	healthServer.SetServingStatus("", healthpb.HealthCheckResponse_SERVING)
	healthServer.SetServingStatus("ecostream.v1.AuthService", healthpb.HealthCheckResponse_SERVING)
	healthServer.SetServingStatus("ecostream.v1.MatchmakingService", healthpb.HealthCheckResponse_SERVING)
	healthpb.RegisterHealthServer(grpcServer, healthServer)

	// Server Reflection para herramientas de inspección (grpcurl, Postman)
	reflection.Register(grpcServer)

	grpcListener, err := net.Listen("tcp", fmt.Sprintf(":%s", cfg.GRPCPort))
	if err != nil {
		log.Fatalf("[FATAL] Fallo al enlazar puerto gRPC %s: %v", cfg.GRPCPort, err)
	}

	go func() {
		log.Printf("[INFO] [gRPC] Servidor gRPC escuchando en 0.0.0.0:%s", cfg.GRPCPort)
		if err := grpcServer.Serve(grpcListener); err != nil {
			log.Printf("[ERROR] [gRPC] Servidor gRPC finalizado: %v", err)
		}
	}()

	// 9. Configurar Servidor HTTP / REST
	router := internalhttp.NewRouter(authService, matchService, db, redisClient, pool)
	httpServer := internalhttp.NewServer(cfg.HTTPPort, router)

	go func() {
		if err := httpServer.Start(); err != nil {
			log.Printf("[ERROR] [HTTP] Servidor HTTP finalizado: %v", err)
		}
	}()

	// 10. Gestión de Señales para Graceful Shutdown
	stopSig := make(chan os.Signal, 1)
	signal.Notify(stopSig, syscall.SIGINT, syscall.SIGTERM)

	sig := <-stopSig
	log.Printf("[INFO] Señal de terminación recibida: %v. Iniciando apagado ordenado...", sig)

	// Apagar HTTP con timeout
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := httpServer.Shutdown(shutdownCtx); err != nil {
		log.Printf("[WARN] Error al apagar servidor HTTP: %v", err)
	}

	// Detener gRPC limpiamente
	log.Println("[INFO] Deteniendo servidor gRPC...")
	grpcServer.GracefulStop()

	// Drenar y apagar worker pool
	log.Println("[INFO] Deteniendo Worker Pool y drenando cola de persistencia...")
	pool.Stop(3 * time.Second)

	log.Println("[INFO] Gateway Go finalizado correctamente.")
}
