package health

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/Makmadon/ecostream-3r/gateway-go/internal/circuitbreaker"
)

func TestLivenessHandler(t *testing.T) {
	h := NewHandler(nil, nil, nil)
	req := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	w := httptest.NewRecorder()

	h.LivenessHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("se esperaba 200 OK en /healthz, se obtuvo: %d", w.Code)
	}

	var resp map[string]interface{}
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("error decodificando json: %v", err)
	}

	if resp["status"] != "UP" {
		t.Errorf("se esperaba status UP, obtenido: %v", resp["status"])
	}
}

func TestReadinessHandler_CircuitBreakerOpenTripsTo503(t *testing.T) {
	dbCB := circuitbreaker.New("test-db-breaker", 3, 5*time.Second)
	rustCB := circuitbreaker.New("test-rust-breaker", 3, 5*time.Second)

	// Simular que el breaker de DB se activó (Postgres caído)
	dbCB.Trip()

	h := NewHandler(nil, dbCB, rustCB)
	req := httptest.NewRequest(http.MethodGet, "/readyz", nil)
	w := httptest.NewRecorder()

	h.ReadinessHandler(w, req)

	if w.Code != http.StatusServiceUnavailable {
		t.Fatalf("se esperaba 503 Service Unavailable al estar el circuit breaker abierto, obtenido: %d", w.Code)
	}

	var resp map[string]interface{}
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("error decodificando json: %v", err)
	}

	if resp["status"] != "CIRCUIT_BREAKER_OPEN_DATABASE_DEGRADED" {
		t.Errorf("se esperaba status CIRCUIT_BREAKER_OPEN_DATABASE_DEGRADED, obtenido: %v", resp["status"])
	}

	if resp["db_circuit_breaker"] != "OPEN (Tripped/Failed)" {
		t.Errorf("se esperaba db_circuit_breaker OPEN, obtenido: %v", resp["db_circuit_breaker"])
	}
}
