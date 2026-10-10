package syncclient

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"
)

// PlayerScoreSync representa las estadísticas de un jugador en la partida finalizada
type PlayerScoreSync struct {
	PlayerID            string  `json:"player_id"`
	Username            string  `json:"username"`
	Role                int32   `json:"role"`
	IndividualPoints    uint32  `json:"individual_points"`
	RepairsDone         uint32  `json:"repairs_done"`
	WaterSavedLiters    float32 `json:"water_saved_liters"`
	WaterRecycledLiters float32 `json:"water_recycled_liters"`
}

// MatchSyncPayload contiene el balance hídrico y las estadísticas finales para la nube
type MatchSyncPayload struct {
	MatchID             string            `json:"match_id"`
	RoomID              string            `json:"room_id"`
	IsVictory           bool              `json:"is_victory"`
	Reason              string            `json:"reason"`
	FinalScore          uint32            `json:"final_score"`
	ReservoirLevelPct   float32           `json:"reservoir_level_pct"`
	WaterPurityPct      float32           `json:"water_purity_pct"`
	TotalLitersSaved    float32           `json:"total_liters_saved"`
	TotalLitersReused   float32           `json:"total_liters_reused"`
	TotalLitersRecycled float32           `json:"total_liters_recycled"`
	PlayerScores        []PlayerScoreSync `json:"player_scores"`
	FinishedAt          time.Time         `json:"finished_at"`
}

// Client gestiona el envío saliente de partidas hacia la base de datos central en Render
type Client struct {
	cloudURL   string
	syncKey    string
	httpClient *http.Client
	enabled    bool
}

// NewClient inicializa el cliente de sincronización hacia Render
func NewClient(cloudURL, syncKey string, enabled bool) *Client {
	return &Client{
		cloudURL:   strings.TrimRight(cloudURL, "/"),
		syncKey:    syncKey,
		httpClient: &http.Client{Timeout: 8 * time.Second},
		enabled:    enabled,
	}
}

// PushMatchAsync encola el envío a Render en una goroutine no bloqueante con reintentos
func (c *Client) PushMatchAsync(payload MatchSyncPayload) {
	if !c.enabled || c.cloudURL == "" {
		return
	}

	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()

		endpoint := fmt.Sprintf("%s/api/v1/sync/match-result", c.cloudURL)
		body, err := json.Marshal(payload)
		if err != nil {
			log.Printf("[WARN] [SyncClient] Error al serializar payload de match %s: %v", payload.MatchID, err)
			return
		}

		maxRetries := 3
		backoff := 2 * time.Second

		for attempt := 1; attempt <= maxRetries; attempt++ {
			select {
			case <-ctx.Done():
				log.Printf("[WARN] [SyncClient] Timeout global al sincronizar match %s a la nube", payload.MatchID)
				return
			default:
			}

			log.Printf("[INFO] [SyncClient] Enviando partida %s a la nube (Intento %d/%d) -> %s",
				payload.MatchID, attempt, maxRetries, endpoint)

			req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewBuffer(body))
			if err != nil {
				log.Printf("[ERROR] [SyncClient] Error al crear request HTTP: %v", err)
				return
			}
			req.Header.Set("Content-Type", "application/json")
			req.Header.Set("X-Sync-Key", c.syncKey)

			resp, err := c.httpClient.Do(req)
			if err == nil {
				if resp.StatusCode == http.StatusOK || resp.StatusCode == http.StatusCreated {
					resp.Body.Close()
					log.Printf("[INFO] [SyncClient] ¡Partida %s sincronizada con éxito en la Nube (Render)! Status: %d",
						payload.MatchID, resp.StatusCode)
					return
				}
				log.Printf("[WARN] [SyncClient] Nube respondió con status %d para match %s", resp.StatusCode, payload.MatchID)
				resp.Body.Close()
			} else {
				log.Printf("[WARN] [SyncClient] Error de red al contactar nube (Intento %d): %v", attempt, err)
			}

			if attempt < maxRetries {
				time.Sleep(backoff)
				backoff *= 2
			}
		}

		log.Printf("[ERROR] [SyncClient] No fue posible sincronizar partida %s a la nube tras %d intentos.",
			payload.MatchID, maxRetries)
	}()
}
