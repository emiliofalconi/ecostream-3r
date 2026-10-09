package leaderboard

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/Makmadon/ecostream-3r/gateway-go/internal/circuitbreaker"
)

func TestLeaderboard_DegradedModeWhenPostgresDown(t *testing.T) {
	cb := circuitbreaker.New("db-breaker-test", 3, 5*time.Second)
	// Simular que Postgres está caído y el circuit breaker se disparó
	cb.Trip()

	service := NewService(nil, nil, nil, cb)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/leaderboard", nil)
	w := httptest.NewRecorder()

	service.GetLeaderboardHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("se esperaba 200 OK con fallback degradado, obtenido: %d", w.Code)
	}

	var resp map[string]interface{}
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("error leyendo respuesta json: %v", err)
	}

	if resp["source"] != "circuit_breaker_degraded_mode" {
		t.Errorf("se esperaba source circuit_breaker_degraded_mode, obtenido: %v", resp["source"])
	}

	leaderboard, ok := resp["leaderboard"].([]interface{})
	if !ok || len(leaderboard) == 0 {
		t.Fatalf("se esperaba lista de leaderboard en modo degradado, obtenido: %v", resp["leaderboard"])
	}
}

func TestMatchHistory_DegradedModeWhenPostgresDown(t *testing.T) {
	cb := circuitbreaker.New("db-breaker-test", 3, 5*time.Second)
	cb.Trip()

	service := NewService(nil, nil, nil, cb)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/matches/history", nil)
	w := httptest.NewRecorder()

	service.GetMatchHistoryHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("se esperaba 200 OK con fallback degradado, obtenido: %d", w.Code)
	}

	var resp map[string]interface{}
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("error leyendo respuesta json: %v", err)
	}

	if resp["source"] != "circuit_breaker_degraded_mode" {
		t.Errorf("se esperaba source circuit_breaker_degraded_mode, obtenido: %v", resp["source"])
	}
}

func TestFinishMatch_NonBlockingWhenPostgresDown(t *testing.T) {
	cb := circuitbreaker.New("db-breaker-test", 3, 5*time.Second)
	cb.Trip()

	service := NewService(nil, nil, nil, cb)

	reqPayload := RecordMatchReq{
		RoomCode:        "TEST-AGUA",
		IsVictory:       true,
		FinalScore:      1200,
		DurationSeconds: 60,
	}
	body, _ := json.Marshal(reqPayload)

	req := httptest.NewRequest(http.MethodPost, "/api/v1/matches/finish", bytes.NewReader(body))
	w := httptest.NewRecorder()

	service.FinishMatchHandler(w, req)

	if w.Code != http.StatusAccepted {
		t.Fatalf("se esperaba 202 Accepted no-bloqueante, obtenido: %d", w.Code)
	}
}
