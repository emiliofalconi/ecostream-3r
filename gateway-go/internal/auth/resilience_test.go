package auth

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/Makmadon/ecostream-3r/gateway-go/internal/circuitbreaker"
)

func TestAuth_FastFail503WhenCircuitBreakerOpen(t *testing.T) {
	cb := circuitbreaker.New("auth-db-breaker", 3, 5*time.Second)
	// Simular falla de Postgres
	cb.Trip()

	service := NewService(nil, "test_secret_123", 24, cb)

	loginBody, _ := json.Marshal(LoginReq{
		UsernameOrEmail: "testuser",
		Password:        "Password123!",
	})

	req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", bytes.NewReader(loginBody))
	w := httptest.NewRecorder()

	service.LoginHandler(w, req)

	if w.Code != http.StatusServiceUnavailable {
		t.Fatalf("se esperaba 503 Service Unavailable con Circuit Breaker OPEN, obtenido: %d", w.Code)
	}

	var resp AuthResp
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("error leyendo respuesta json: %v", err)
	}

	if resp.Success != false {
		t.Errorf("se esperaba success = false")
	}
}
