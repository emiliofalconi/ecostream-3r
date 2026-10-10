package http

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestSyncMatchResult_UnauthorizedWithoutKey(t *testing.T) {
	router := &Router{
		syncKey: "secret_sync_key_test_123",
		mux:     http.NewServeMux(),
	}
	router.registerRoutes()

	payload := MatchSyncPayload{
		MatchID:    "mtc_test_01",
		RoomID:     "room_test",
		IsVictory:  true,
		FinalScore: 1200,
		FinishedAt: time.Now(),
	}
	body, _ := json.Marshal(payload)

	// 1. Petición sin cabecera X-Sync-Key
	req, _ := http.NewRequest(http.MethodPost, "/api/v1/sync/match-result", bytes.NewBuffer(body))
	w := httptest.NewRecorder()
	router.mux.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Fatalf("Esperaba status 401 Unauthorized, pero obtuvo %d", w.Code)
	}

	// 2. Petición con X-Sync-Key erróneo
	req2, _ := http.NewRequest(http.MethodPost, "/api/v1/sync/match-result", bytes.NewBuffer(body))
	req2.Header.Set("X-Sync-Key", "clave_incorrecta")
	w2 := httptest.NewRecorder()
	router.mux.ServeHTTP(w2, req2)

	if w2.Code != http.StatusUnauthorized {
		t.Fatalf("Esperaba status 401 Unauthorized, pero obtuvo %d", w2.Code)
	}
}

func TestSyncMatchResult_MethodNotAllowed(t *testing.T) {
	router := &Router{
		syncKey: "secret_sync_key_test_123",
		mux:     http.NewServeMux(),
	}
	router.registerRoutes()

	req, _ := http.NewRequest(http.MethodGet, "/api/v1/sync/match-result", nil)
	w := httptest.NewRecorder()
	router.mux.ServeHTTP(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("Esperaba status 405 MethodNotAllowed para GET, pero obtuvo %d", w.Code)
	}
}
