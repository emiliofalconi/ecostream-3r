package http

import (
	"context"
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/Makmadon/ecostream-3r/gateway-go/internal/auth"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/matchmaking"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/storage"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/workerpool"
	ecostreamv1 "github.com/Makmadon/ecostream-3r/gateway-go/proto/v1"
)

// Router agrupa las dependencias necesarias para las rutas HTTP
type Router struct {
	authService *auth.Service
	matchService *matchmaking.Service
	db          *storage.PostgresDB
	redis       *storage.RedisClient
	pool        *workerpool.WorkerPool
	mux         *http.ServeMux
}

// NewRouter crea e inicializa el router HTTP
func NewRouter(
	authService *auth.Service,
	matchService *matchmaking.Service,
	db *storage.PostgresDB,
	redis *storage.RedisClient,
	pool *workerpool.WorkerPool,
) *Router {
	r := &Router{
		authService:  authService,
		matchService: matchService,
		db:           db,
		redis:        redis,
		pool:         pool,
		mux:          http.NewServeMux(),
	}
	r.registerRoutes()
	return r
}

func (r *Router) Handler() http.Handler {
	return corsMiddleware(r.mux)
}

func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if req.Method == http.MethodOptions {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, req)
	})
}

func writeJSON(w http.ResponseWriter, statusCode int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	_ = json.NewEncoder(w).Encode(data)
}

func (r *Router) registerRoutes() {
	// -------------------------------------------------------------
	// Health & Liveness / Readiness
	// -------------------------------------------------------------
	r.mux.HandleFunc("/healthz", func(w http.ResponseWriter, req *http.Request) {
		writeJSON(w, http.StatusOK, map[string]interface{}{
			"status":    "UP",
			"timestamp": time.Now().Format(time.RFC3339),
			"service":   "gateway-go",
		})
	})

	r.mux.HandleFunc("/readyz", func(w http.ResponseWriter, req *http.Request) {
		ctx, cancel := context.WithTimeout(req.Context(), 2*time.Second)
		defer cancel()

		dbErr := r.db.Ping(ctx)
		redisErr := r.redis.Ping(ctx)

		status := "READY"
		statusCode := http.StatusOK

		if dbErr != nil {
			status = "NOT_READY"
			statusCode = http.StatusServiceUnavailable
		}

		redisStatus := "CONNECTED"
		if redisErr != nil {
			redisStatus = "DEGRADED" // Redis caído es advertencia no fatídica
		}

		writeJSON(w, statusCode, map[string]interface{}{
			"status":     status,
			"database":   map[string]interface{}{"status": ternary(dbErr == nil, "CONNECTED", "DISCONNECTED")},
			"redis":      map[string]interface{}{"status": redisStatus},
			"workerpool": r.pool.Metrics(),
		})
	})

	// -------------------------------------------------------------
	// Telemetría & Métricas
	// -------------------------------------------------------------
	r.mux.HandleFunc("/api/v1/stats/metrics", func(w http.ResponseWriter, req *http.Request) {
		writeJSON(w, http.StatusOK, map[string]interface{}{
			"worker_pool": r.pool.Metrics(),
			"uptime":      time.Now().Format(time.RFC3339),
		})
	})

	// -------------------------------------------------------------
	// Autenticación HTTP
	// -------------------------------------------------------------
	r.mux.HandleFunc("/api/v1/auth/register", func(w http.ResponseWriter, req *http.Request) {
		if req.Method != http.MethodPost {
			http.Error(w, "Método no permitido", http.StatusMethodNotAllowed)
			return
		}
		var body struct {
			Username string `json:"username"`
			Email    string `json:"email"`
			Password string `json:"password"`
			Role     int    `json:"role"`
		}
		if err := json.NewDecoder(req.Body).Decode(&body); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "JSON inválido"})
			return
		}

		user, token, expiresAt, err := r.authService.Register(req.Context(), body.Username, body.Email, body.Password, ecostreamv1.PlayerRole(body.Role))
		if err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}

		writeJSON(w, http.StatusCreated, map[string]interface{}{
			"success":    true,
			"token":      token,
			"expires_at": expiresAt,
			"user":       user,
		})
	})

	r.mux.HandleFunc("/api/v1/auth/login", func(w http.ResponseWriter, req *http.Request) {
		if req.Method != http.MethodPost {
			http.Error(w, "Método no permitido", http.StatusMethodNotAllowed)
			return
		}
		var body struct {
			UsernameOrEmail string `json:"username_or_email"`
			Password        string `json:"password"`
		}
		if err := json.NewDecoder(req.Body).Decode(&body); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "JSON inválido"})
			return
		}

		user, token, expiresAt, err := r.authService.Login(req.Context(), body.UsernameOrEmail, body.Password)
		if err != nil {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": err.Error()})
			return
		}

		writeJSON(w, http.StatusOK, map[string]interface{}{
			"success":    true,
			"token":      token,
			"expires_at": expiresAt,
			"user":       user,
		})
	})

	r.mux.HandleFunc("/api/v1/auth/verify", func(w http.ResponseWriter, req *http.Request) {
		token := extractToken(req)
		if token == "" {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "Token no proporcionado"})
			return
		}
		claims, err := r.authService.VerifyToken(token)
		if err != nil {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": err.Error()})
			return
		}
		writeJSON(w, http.StatusOK, map[string]interface{}{
			"valid":    true,
			"user_id":  claims.UserID,
			"username": claims.Username,
			"role":     claims.Role,
		})
	})

	r.mux.HandleFunc("/api/v1/auth/profile", func(w http.ResponseWriter, req *http.Request) {
		token := extractToken(req)
		claims, err := r.authService.VerifyToken(token)
		if err != nil {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "No autorizado"})
			return
		}
		user, err := r.authService.GetProfile(req.Context(), claims.UserID)
		if err != nil {
			writeJSON(w, http.StatusNotFound, map[string]string{"error": err.Error()})
			return
		}
		writeJSON(w, http.StatusOK, user)
	})

	// -------------------------------------------------------------
	// Matchmaking y Lobbies HTTP
	// -------------------------------------------------------------
	r.mux.HandleFunc("/api/v1/rooms/create", func(w http.ResponseWriter, req *http.Request) {
		if req.Method != http.MethodPost {
			http.Error(w, "Método no permitido", http.StatusMethodNotAllowed)
			return
		}
		token := extractToken(req)
		claims, err := r.authService.VerifyToken(token)
		if err != nil {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "No autorizado"})
			return
		}

		var body struct {
			RoomName   string `json:"room_name"`
			Role       int    `json:"role"`
			MaxPlayers uint32 `json:"max_players"`
			Difficulty uint32 `json:"difficulty"`
		}
		_ = json.NewDecoder(req.Body).Decode(&body)

		role := ecostreamv1.PlayerRole(body.Role)
		if role == ecostreamv1.PlayerRole_ROLE_UNSPECIFIED {
			role = ecostreamv1.PlayerRole(claims.Role)
		}

		room, ticket, err := r.matchService.CreateRoom(req.Context(), claims.UserID, claims.Username, body.RoomName, role, body.MaxPlayers, body.Difficulty)
		if err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}

		writeJSON(w, http.StatusCreated, map[string]interface{}{
			"success":     true,
			"room":        room,
			"room_ticket": ticket,
		})
	})

	r.mux.HandleFunc("/api/v1/rooms/join", func(w http.ResponseWriter, req *http.Request) {
		if req.Method != http.MethodPost {
			http.Error(w, "Método no permitido", http.StatusMethodNotAllowed)
			return
		}
		token := extractToken(req)
		claims, err := r.authService.VerifyToken(token)
		if err != nil {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "No autorizado"})
			return
		}

		var body struct {
			RoomCode string `json:"room_code"`
			Role     int    `json:"role"`
		}
		if err := json.NewDecoder(req.Body).Decode(&body); err != nil || body.RoomCode == "" {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "room_code requerido"})
			return
		}

		role := ecostreamv1.PlayerRole(body.Role)
		if role == ecostreamv1.PlayerRole_ROLE_UNSPECIFIED {
			role = ecostreamv1.PlayerRole(claims.Role)
		}

		room, ticket, err := r.matchService.JoinRoom(req.Context(), body.RoomCode, claims.UserID, claims.Username, role)
		if err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}

		writeJSON(w, http.StatusOK, map[string]interface{}{
			"success":     true,
			"room":        room,
			"room_ticket": ticket,
		})
	})

	r.mux.HandleFunc("/api/v1/rooms/quick", func(w http.ResponseWriter, req *http.Request) {
		if req.Method != http.MethodPost {
			http.Error(w, "Método no permitido", http.StatusMethodNotAllowed)
			return
		}
		token := extractToken(req)
		claims, err := r.authService.VerifyToken(token)
		if err != nil {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "No autorizado"})
			return
		}

		var body struct {
			Role int `json:"role"`
		}
		_ = json.NewDecoder(req.Body).Decode(&body)

		role := ecostreamv1.PlayerRole(body.Role)
		if role == ecostreamv1.PlayerRole_ROLE_UNSPECIFIED {
			role = ecostreamv1.PlayerRole(claims.Role)
		}

		room, ticket, err := r.matchService.QuickMatch(req.Context(), claims.UserID, claims.Username, role)
		if err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}

		writeJSON(w, http.StatusOK, map[string]interface{}{
			"success":     true,
			"room":        room,
			"room_ticket": ticket,
		})
	})

	r.mux.HandleFunc("/api/v1/rooms/list", func(w http.ResponseWriter, req *http.Request) {
		pageSizeStr := req.URL.Query().Get("page_size")
		pageSize := 20
		if val, err := strconv.Atoi(pageSizeStr); err == nil && val > 0 {
			pageSize = val
		}

		rooms, err := r.matchService.ListAvailableRooms(req.Context(), uint32(pageSize))
		if err != nil {
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": err.Error()})
			return
		}

		writeJSON(w, http.StatusOK, map[string]interface{}{
			"success": true,
			"rooms":   rooms,
		})
	})

	r.mux.HandleFunc("/api/v1/rooms/status", func(w http.ResponseWriter, req *http.Request) {
		roomID := req.URL.Query().Get("room_id")
		if roomID == "" {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "room_id requerido"})
			return
		}

		room, err := r.matchService.GetRoomStatus(req.Context(), roomID)
		if err != nil {
			writeJSON(w, http.StatusNotFound, map[string]string{"error": err.Error()})
			return
		}

		writeJSON(w, http.StatusOK, map[string]interface{}{
			"success": true,
			"room":    room,
		})
	})

	r.mux.HandleFunc("/api/v1/rooms/start", func(w http.ResponseWriter, req *http.Request) {
		if req.Method != http.MethodPost {
			http.Error(w, "Método no permitido", http.StatusMethodNotAllowed)
			return
		}
		token := extractToken(req)
		claims, err := r.authService.VerifyToken(token)
		if err != nil {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "No autorizado"})
			return
		}

		var body struct {
			RoomID       string `json:"room_id"`
			FillWithBots bool   `json:"fill_with_bots"`
		}
		if err := json.NewDecoder(req.Body).Decode(&body); err != nil || body.RoomID == "" {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "room_id requerido"})
			return
		}

		room, ticket, err := r.matchService.StartMatch(req.Context(), body.RoomID, claims.UserID, body.FillWithBots)
		if err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}

		writeJSON(w, http.StatusOK, map[string]interface{}{
			"success":     true,
			"room":        room,
			"room_ticket": ticket,
		})
	})
}

func extractToken(req *http.Request) string {
	authHeader := req.Header.Get("Authorization")
	if strings.HasPrefix(authHeader, "Bearer ") {
		return strings.TrimPrefix(authHeader, "Bearer ")
	}
	return req.URL.Query().Get("token")
}

func ternary(cond bool, a, b string) string {
	if cond {
		return a
	}
	return b
}
