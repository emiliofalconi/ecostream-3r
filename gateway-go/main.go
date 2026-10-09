package main

import (
	"context"
	"database/sql"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/Makmadon/ecostream-3r/gateway-go/internal/auth"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/circuitbreaker"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/config"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/database"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/health"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/leaderboard"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/matchmaking"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/swagger"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/workers"
)

// Middleware CORS
func enableCORS(allowedOrigins string, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", allowedOrigins)
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")

		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusOK)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func main() {
	log.Println("=============================================================")
	log.Println("🌱 ECOSTREAM 3R - CONTROL PLANE & GATEWAY (Go 1.22+)")
	log.Println("=============================================================")

	cfg := config.LoadConfig()

	// 1. Inicializar Circuit Breakers
	dbCB := circuitbreaker.New("PostgreSQL-Breaker", 3, 5*time.Second)
	rustCB := circuitbreaker.New("Rust-Engine-Breaker", 3, 3*time.Second)

	// 2. Conectar a PostgreSQL 16
	db, err := database.Connect(cfg.DatabaseURL)
	if err != nil {
		log.Printf("[DATABASE WARN] Arrancando con base de datos en modo degradado: %v", err)
	} else if db != nil {
		db.WithBreaker(dbCB)
	}

	var sqlDB *sql.DB
	if db != nil && db.DB != nil {
		sqlDB = db.DB
	}

	// 3. Iniciar Worker Pool de Goroutines para Auditoría
	var auditPool *workers.AuditWorkerPool
	if sqlDB != nil {
		auditPool = workers.NewAuditWorkerPool(sqlDB, 5, 100)
		auditPool.Start()
		defer auditPool.Stop()
	}

	// 4. Inicializar Servicios protegidos con Circuit Breaker y Timeouts
	authService := auth.NewService(sqlDB, cfg.JWTSecret, cfg.JWTExpirationHours, dbCB)
	matchmakingService := matchmaking.NewService(sqlDB, authService, cfg.SimulationWorker, dbCB)
	leaderboardService := leaderboard.NewService(sqlDB, authService, auditPool, dbCB)
	healthHandler := health.NewHandler(db, dbCB, rustCB)
	swaggerHandler := swagger.NewHandler("docs/swagger/openapi.json")

	// 5. Configurar Enrutador
	mux := http.NewServeMux()

	// Endpoints de Salud (Health Checks)
	mux.HandleFunc("/healthz", healthHandler.LivenessHandler)
	mux.HandleFunc("/readyz", healthHandler.ReadinessHandler)

	// Swagger UI
	mux.HandleFunc("/swagger/", swaggerHandler.UIHandler)
	mux.HandleFunc("/swagger/openapi.json", swaggerHandler.SpecHandler)

	// API REST de Autenticación
	mux.HandleFunc("/api/v1/auth/register", authService.RegisterHandler)
	mux.HandleFunc("/api/v1/auth/login", authService.LoginHandler)

	// API REST de Matchmaking
	mux.HandleFunc("/api/v1/rooms", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			matchmakingService.CreateRoomHandler(w, r)
		} else {
			matchmakingService.ListRoomsHandler(w, r)
		}
	})
	mux.HandleFunc("/api/v1/rooms/join", matchmakingService.JoinRoomHandler)

	// API REST de Partidas y Leaderboards (No bloqueante con Goroutines)
	mux.HandleFunc("/api/v1/leaderboard", leaderboardService.GetLeaderboardHandler)
	mux.HandleFunc("/api/v1/matches/finish", leaderboardService.FinishMatchHandler)
	mux.HandleFunc("/api/v1/matches/history", leaderboardService.GetMatchHistoryHandler)

	// 6. Servidor HTTP
	server := &http.Server{
		Addr:         ":" + cfg.HTTPPort,
		Handler:      enableCORS(cfg.AllowedOrigins, mux),
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// 7. Arranque en Goroutine
	go func() {
		log.Printf("[GATEWAY HTTP] Servidor escuchando en http://0.0.0.0:%s", cfg.HTTPPort)
		log.Printf("[SWAGGER UI] Documentación interactiva en http://localhost:%s/swagger/", cfg.HTTPPort)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("[FATAL] Error en servidor HTTP: %v", err)
		}
	}()

	// 8. Graceful Shutdown (Apagado Limpio)
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("\n[GATEWAY] Apagando servidor de forma limpia...")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		log.Printf("[GATEWAY ERROR] Error durante el apagado: %v", err)
	}

	if db != nil && db.DB != nil {
		db.Close()
	}

	log.Println("[GATEWAY] Servidor apagado exitosamente.")
}
