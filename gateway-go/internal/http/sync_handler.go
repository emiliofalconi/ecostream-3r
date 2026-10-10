package http

import (
	"encoding/json"
	"log"
	"net/http"
	"time"
)

// PlayerScoreSync representa las estadísticas individuales de un jugador recibidas desde el servidor local
type PlayerScoreSync struct {
	PlayerID            string  `json:"player_id"`
	Username            string  `json:"username"`
	Role                int32   `json:"role"`
	IndividualPoints    uint32  `json:"individual_points"`
	RepairsDone         uint32  `json:"repairs_done"`
	WaterSavedLiters    float32 `json:"water_saved_liters"`
	WaterRecycledLiters float32 `json:"water_recycled_liters"`
}

// MatchSyncPayload define el payload enviado por el Gateway local al terminar una partida
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

// handleSyncMatchResult procesa la sincronización segura de partidas desde el Gateway local hacia la Nube
func (r *Router) handleSyncMatchResult(w http.ResponseWriter, req *http.Request) {
	if req.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "Método no permitido"})
		return
	}

	// 1. Verificación de Autenticación Server-to-Server
	syncKeyHeader := req.Header.Get("X-Sync-Key")
	if r.syncKey != "" && syncKeyHeader != r.syncKey {
		log.Printf("[SECURITY] [Sync] Intento de sincronización rechazado: X-Sync-Key inválido o ausente")
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "No autorizado: X-Sync-Key inválido"})
		return
	}

	var payload MatchSyncPayload
	if err := json.NewDecoder(req.Body).Decode(&payload); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "Payload JSON inválido"})
		return
	}

	if payload.MatchID == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "match_id requerido"})
		return
	}

	ctx := req.Context()

	// 2. Comprobar Idempotencia: ¿Ya se había sincronizado esta partida?
	var existingID string
	err := r.db.DB.QueryRowContext(ctx, "SELECT id FROM matches WHERE id = $1", payload.MatchID).Scan(&existingID)
	if err == nil && existingID != "" {
		log.Printf("[INFO] [Sync] Partida %s ya existía en la nube. Operación idempotente omitida.", payload.MatchID)
		writeJSON(w, http.StatusOK, map[string]interface{}{
			"status":   "already_synced",
			"match_id": payload.MatchID,
			"message":  "Partida ya registrada previamente",
		})
		return
	}

	// 3. Inserción atómica transaccional en PostgreSQL de la Nube
	tx, err := r.db.DB.BeginTx(ctx, nil)
	if err != nil {
		log.Printf("[ERROR] [Sync] Error al iniciar transacción SQL: %v", err)
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "Error interno de base de datos"})
		return
	}
	defer tx.Rollback()

	queryMatch := `
		INSERT INTO matches (
			id, room_id, is_victory, end_reason, final_score,
			final_reservoir_pct, final_water_purity_pct,
			total_liters_saved, total_liters_reused, total_liters_recycled,
			started_at, finished_at
		) VALUES (
			$1, $2, $3, $4, $5,
			$6, $7,
			$8, $9, $10,
			NOW() - INTERVAL '5 minutes', NOW()
		)
		ON CONFLICT (id) DO NOTHING
	`
	_, err = tx.ExecContext(ctx, queryMatch,
		payload.MatchID,
		payload.RoomID,
		payload.IsVictory,
		payload.Reason,
		payload.FinalScore,
		payload.ReservoirLevelPct,
		payload.WaterPurityPct,
		payload.TotalLitersSaved,
		payload.TotalLitersReused,
		payload.TotalLitersRecycled,
	)
	if err != nil {
		log.Printf("[ERROR] [Sync] Fallo al insertar partida sincronizada: %v", err)
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "Fallo al insertar match"})
		return
	}

	// 4. Upsert de jugadores y actualización de eco-estadísticas globales
	wonInc := 0
	if payload.IsVictory {
		wonInc = 1
	}

	for _, p := range payload.PlayerScores {
		// Asegurar que el usuario existe en la nube (creación automática por nickname)
		queryUpsertUser := `
			INSERT INTO users (id, username, total_eco_score, games_played, games_won, created_at, updated_at)
			VALUES ($1, $2, 0, 0, 0, NOW(), NOW())
			ON CONFLICT (id) DO NOTHING
		`
		_, _ = tx.ExecContext(ctx, queryUpsertUser, p.PlayerID, p.Username)

		// Insertar estadísticas de la partida
		queryStats := `
			INSERT INTO match_player_stats (
				match_id, user_id, username, role_played,
				repairs_done, water_saved_liters, water_recycled_liters, individual_points
			) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
			ON CONFLICT DO NOTHING
		`
		_, _ = tx.ExecContext(ctx, queryStats,
			payload.MatchID,
			p.PlayerID,
			p.Username,
			p.Role,
			p.RepairsDone,
			p.WaterSavedLiters,
			p.WaterRecycledLiters,
			p.IndividualPoints,
		)

		// Incrementar estadísticas acumuladas del usuario en la nube
		queryUserUpdate := `
			UPDATE users
			SET games_played = games_played + 1,
			    games_won = games_won + $1,
			    total_eco_score = total_eco_score + $2,
			    updated_at = NOW()
			WHERE id = $3
		`
		_, _ = tx.ExecContext(ctx, queryUserUpdate, wonInc, p.IndividualPoints, p.PlayerID)
	}

	if err := tx.Commit(); err != nil {
		log.Printf("[ERROR] [Sync] Fallo al confirmar transacción de sincronización: %v", err)
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "Fallo al confirmar transacción"})
		return
	}

	log.Printf("[INFO] [Sync] Partida %s sincronizada exitosamente en la nube. Total jugadores: %d, Victoria: %v",
		payload.MatchID, len(payload.PlayerScores), payload.IsVictory)

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"status":   "success",
		"match_id": payload.MatchID,
		"message":  "Partida y estadísticas sincronizadas exitosamente en la base de datos de la nube",
	})
}
