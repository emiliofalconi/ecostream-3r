package coordinator

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/google/uuid"

	"github.com/Makmadon/ecostream-3r/gateway-go/internal/storage"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/syncclient"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/workerpool"
	ecostreamv1 "github.com/Makmadon/ecostream-3r/gateway-go/proto/v1"
)

// Handler implementa el servicio gRPC interno que recibe notificaciones de Rust
type Handler struct {
	ecostreamv1.UnimplementedInternalCoordinatorServiceServer
	db         *storage.PostgresDB
	redis      *storage.RedisClient
	workerPool *workerpool.WorkerPool
	syncClient *syncclient.Client
}

// NewHandler inicializa el coordinador interno
func NewHandler(db *storage.PostgresDB, redis *storage.RedisClient, pool *workerpool.WorkerPool, syncClient *syncclient.Client) *Handler {
	return &Handler{
		db:         db,
		redis:      redis,
		workerPool: pool,
		syncClient: syncClient,
	}
}

// ProvisionRoom maneja la solicitud de aprovisionamiento de sala (si Go decide invocar a Rust o viceversa)
func (h *Handler) ProvisionRoom(ctx context.Context, req *ecostreamv1.ProvisionRoomRequest) (*ecostreamv1.ProvisionRoomResponse, error) {
	return &ecostreamv1.ProvisionRoomResponse{
		Success:            true,
		Message:            "Sala aprovisionada para simulación",
		SimulationEndpoint: "localhost:50052",
	}, nil
}

// NotifyMatchFinished procesa el fin de partida emitido por el motor de Rust
func (h *Handler) NotifyMatchFinished(ctx context.Context, req *ecostreamv1.NotifyMatchFinishedRequest) (*ecostreamv1.NotifyMatchFinishedResponse, error) {
	if req.FinalState == nil {
		return &ecostreamv1.NotifyMatchFinishedResponse{
			Acknowledged: false,
			Message:      "Estado final nulo",
		}, nil
	}

	matchID := "mtc_" + uuid.New().String()[:16]
	finalState := req.FinalState
	metrics := finalState.FinalMetrics
	if metrics == nil {
		metrics = &ecostreamv1.WaterMetrics{}
	}

	tx, err := h.db.DB.BeginTx(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("error al iniciar transacción de cierre de partida: %w", err)
	}
	defer tx.Rollback()

	// 1. Insertar registro de la partida en matches
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
	`
	_, err = tx.ExecContext(ctx, queryMatch,
		matchID,
		req.RoomId,
		finalState.IsVictory,
		finalState.Reason,
		finalState.FinalScore,
		metrics.ReservoirLevelPct,
		metrics.WaterPurityPct,
		metrics.TotalLitersSaved,
		metrics.TotalLitersReused,
		metrics.TotalLitersRecycled,
	)
	if err != nil {
		log.Printf("[ERROR] [Coordinator] Error al insertar match: %v", err)
		return nil, err
	}

	// 2. Guardar estadísticas individuales de jugadores y actualizar perfiles
	for _, p := range finalState.PlayerScores {
		queryStats := `
			INSERT INTO match_player_stats (
				match_id, user_id, username, role_played,
				repairs_done, water_saved_liters, water_recycled_liters, individual_points
			) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
		`
		_, _ = tx.ExecContext(ctx, queryStats,
			matchID,
			p.PlayerId,
			p.Username,
			int32(p.Role),
			p.RepairsDone,
			p.WaterSavedLiters,
			p.WaterRecycledLiters,
			p.IndividualPoints,
		)

		// Actualizar estadísticas globales del jugador en users
		wonInc := 0
		if finalState.IsVictory {
			wonInc = 1
		}
		queryUserUpdate := `
			UPDATE users
			SET games_played = games_played + 1,
			    games_won = games_won + $1,
			    total_eco_score = total_eco_score + $2,
			    updated_at = NOW()
			WHERE id = $3
		`
		_, _ = tx.ExecContext(ctx, queryUserUpdate, wonInc, p.IndividualPoints, p.PlayerId)
	}

	// 3. Marcar sala como finalizada (status = 4)
	tx.ExecContext(ctx, `UPDATE rooms SET status = 4, updated_at = NOW() WHERE id = $1`, req.RoomId)

	if err := tx.Commit(); err != nil {
		return nil, fmt.Errorf("error al confirmar cierre de partida: %w", err)
	}

	// Invalidar caché
	if h.redis != nil {
		_ = h.redis.InvalidateRoomCache(ctx, req.RoomId)
	}

	if h.workerPool != nil {
		h.workerPool.Enqueue(workerpool.AuditEvent{
			EventType: "MATCH_PERSISTED",
			Severity:  "INFO",
			Payload: map[string]interface{}{
				"match_id":    matchID,
				"room_id":     req.RoomId,
				"is_victory":  finalState.IsVictory,
				"final_score": finalState.FinalScore,
			},
			CreatedAt: time.Now(),
		})
	}

	log.Printf("[INFO] [Coordinator] Partida %s para sala %s persistida exitosamente. Victoria: %v", matchID, req.RoomId, finalState.IsVictory)

	// 4. Sincronizar asíncronamente con la base de datos en la Nube (si está habilitado)
	if h.syncClient != nil {
		var playerScores []syncclient.PlayerScoreSync
		for _, p := range finalState.PlayerScores {
			playerScores = append(playerScores, syncclient.PlayerScoreSync{
				PlayerID:            p.PlayerId,
				Username:            p.Username,
				Role:                int32(p.Role),
				IndividualPoints:    p.IndividualPoints,
				RepairsDone:         p.RepairsDone,
				WaterSavedLiters:    p.WaterSavedLiters,
				WaterRecycledLiters: p.WaterRecycledLiters,
			})
		}

		h.syncClient.PushMatchAsync(syncclient.MatchSyncPayload{
			MatchID:             matchID,
			RoomID:              req.RoomId,
			IsVictory:           finalState.IsVictory,
			Reason:              finalState.Reason,
			FinalScore:          finalState.FinalScore,
			ReservoirLevelPct:   metrics.ReservoirLevelPct,
			WaterPurityPct:      metrics.WaterPurityPct,
			TotalLitersSaved:    metrics.TotalLitersSaved,
			TotalLitersReused:   metrics.TotalLitersReused,
			TotalLitersRecycled: metrics.TotalLitersRecycled,
			PlayerScores:        playerScores,
			FinishedAt:          time.Now(),
		})
	}

	return &ecostreamv1.NotifyMatchFinishedResponse{
		Acknowledged: true,
		Message:      "Partida y balance hídrico persistidos exitosamente en PostgreSQL",
	}, nil
}
