package health

import (
	"encoding/json"
	"net/http"
	"runtime"
	"time"

	"github.com/Makmadon/ecostream-3r/gateway-go/internal/circuitbreaker"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/database"
)

type Handler struct {
	db      *database.DB
	dbCB    *circuitbreaker.CircuitBreaker
	rustCB  *circuitbreaker.CircuitBreaker
}

func NewHandler(db *database.DB, dbCB, rustCB *circuitbreaker.CircuitBreaker) *Handler {
	return &Handler{
		db:     db,
		dbCB:   dbCB,
		rustCB: rustCB,
	}
}

// Liveness Probe (GET /healthz)
func (h *Handler) LivenessHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":     "UP",
		"service":    "gateway-go",
		"goroutines": runtime.NumGoroutine(),
		"timestamp":  time.Now().Format(time.RFC3339),
	})
}

// Readiness Probe (GET /readyz)
func (h *Handler) ReadinessHandler(w http.ResponseWriter, r *http.Request) {
	dbHealthy := false
	if h.db != nil {
		dbHealthy = h.db.PingCheck()
	}
	status := "READY"
	httpCode := http.StatusOK

	if h.dbCB != nil && h.dbCB.State() == circuitbreaker.StateOpen {
		status = "CIRCUIT_BREAKER_OPEN_DATABASE_DEGRADED"
		httpCode = http.StatusServiceUnavailable
	} else if !dbHealthy {
		status = "DEGRADED_DATABASE_UNAVAILABLE"
		httpCode = http.StatusServiceUnavailable
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(httpCode)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":             status,
		"database_connected": dbHealthy,
		"db_circuit_breaker": h.dbCB.GetState(),
		"rust_circuit_breaker": h.rustCB.GetState(),
		"goroutines":         runtime.NumGoroutine(),
		"timestamp":          time.Now().Format(time.RFC3339),
	})
}
