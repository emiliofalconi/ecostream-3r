package matchmaking

import (
	"context"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"log"
	"math/big"
	"strings"
	"time"

	"github.com/google/uuid"

	"github.com/Makmadon/ecostream-3r/gateway-go/internal/auth"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/storage"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/workerpool"
	ecostreamv1 "github.com/Makmadon/ecostream-3r/gateway-go/proto/v1"
)

// Service implementa la lógica de negocio de salas y matchmaking
type Service struct {
	repo          *Repository
	redis         *storage.RedisClient
	ticketManager *auth.TicketManager
	workerPool    *workerpool.WorkerPool
	simulationURL string
}

// NewService inicializa el servicio de matchmaking
func NewService(
	repo *Repository,
	redis *storage.RedisClient,
	ticketManager *auth.TicketManager,
	workerPool *workerpool.WorkerPool,
	simulationURL string,
) *Service {
	if simulationURL == "" {
		simulationURL = "localhost:50052"
	}

	return &Service{
		repo:          repo,
		redis:         redis,
		ticketManager: ticketManager,
		workerPool:    workerPool,
		simulationURL: simulationURL,
	}
}

func generateFriendlyCode() string {
	const charset = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
	b := make([]byte, 6)
	for i := range b {
		num, _ := rand.Int(rand.Reader, big.NewInt(int64(len(charset))))
		b[i] = charset[num.Int64()]
	}
	return string(b)
}

// CreateRoom crea una nueva sala con persistencia y cache
func (s *Service) CreateRoom(
	ctx context.Context,
	hostID, hostUsername string,
	roomName string,
	role ecostreamv1.PlayerRole,
	maxPlayers uint32,
	difficulty uint32,
) (*ecostreamv1.RoomInfo, string, error) {
	if maxPlayers == 0 || maxPlayers > 4 {
		maxPlayers = 4
	}
	if difficulty == 0 {
		difficulty = 1
	}
	if strings.TrimSpace(roomName) == "" {
		roomName = fmt.Sprintf("EcoCuadrilla de %s", hostUsername)
	}

	roomID := "rm_" + strings.ReplaceAll(uuid.New().String(), "-", "")[:16]
	roomCode := generateFriendlyCode()

	room := &ecostreamv1.RoomInfo{
		RoomId:             roomID,
		RoomCode:           roomCode,
		RoomName:           roomName,
		Status:             ecostreamv1.RoomStatus_ROOM_STATUS_WAITING,
		MaxPlayers:         maxPlayers,
		DifficultyLevel:    difficulty,
		SimulationEndpoint: s.simulationURL,
		CreatedAtUnix:      time.Now().Unix(),
		Players: []*ecostreamv1.PlayerSlot{
			{
				UserId:       hostID,
				Username:     hostUsername,
				SelectedRole: role,
				IsHost:       true,
				IsReady:      true,
				IsBot:        false,
			},
		},
	}

	if err := s.repo.CreateRoom(ctx, room, hostID, hostUsername, role); err != nil {
		return nil, "", fmt.Errorf("error al persistir sala: %w", err)
	}

	// Generar RoomTicket firmado criptográficamente con HMAC para el Host
	ticket, err := s.ticketManager.GenerateTicket(roomID, hostID, hostUsername, int32(role), true)
	if err != nil {
		return nil, "", fmt.Errorf("error al generar room ticket: %w", err)
	}

	// Invalida o escribe cache en Redis
	s.cacheRoom(ctx, room)

	if s.workerPool != nil {
		s.workerPool.Enqueue(workerpool.AuditEvent{
			EventType: "ROOM_CREATED",
			Severity:  "INFO",
			Payload: map[string]interface{}{
				"room_id":   roomID,
				"room_code": roomCode,
				"host_id":   hostID,
			},
		})
	}

	return room, ticket, nil
}

// JoinRoom añade de forma atómica a un jugador a una sala existente
func (s *Service) JoinRoom(
	ctx context.Context,
	roomCode string,
	userID, username string,
	role ecostreamv1.PlayerRole,
) (*ecostreamv1.RoomInfo, string, error) {
	roomCode = strings.ToUpper(strings.TrimSpace(roomCode))

	room, err := s.repo.JoinRoomAtomic(ctx, roomCode, userID, username, role)
	if err != nil {
		return nil, "", err
	}

	ticket, err := s.ticketManager.GenerateTicket(room.RoomId, userID, username, int32(role), false)
	if err != nil {
		return nil, "", fmt.Errorf("error al generar ticket de sala: %w", err)
	}

	// Invalidar cache en Redis tras mutación
	if s.redis != nil {
		_ = s.redis.InvalidateRoomCache(ctx, room.RoomCode)
		_ = s.redis.InvalidateRoomCache(ctx, room.RoomId)
	}

	if s.workerPool != nil {
		s.workerPool.Enqueue(workerpool.AuditEvent{
			EventType: "ROOM_JOINED",
			Severity:  "INFO",
			Payload: map[string]interface{}{
				"room_id": room.RoomId,
				"user_id": userID,
			},
		})
	}

	return room, ticket, nil
}

// QuickMatch une a una sala disponible o crea una automáticamente
func (s *Service) QuickMatch(
	ctx context.Context,
	userID, username string,
	role ecostreamv1.PlayerRole,
) (*ecostreamv1.RoomInfo, string, error) {
	code, err := s.repo.FindAvailableRoom(ctx)
	if err == nil && code != "" {
		room, ticket, joinErr := s.JoinRoom(ctx, code, userID, username, role)
		if joinErr == nil {
			return room, ticket, nil
		}
	}

	// Si no hay salas disponibles, crear una nueva sala pública
	return s.CreateRoom(ctx, userID, username, "EcoStream Partida Rápida", role, 4, 1)
}

// LeaveRoom procesa la salida de un jugador
func (s *Service) LeaveRoom(ctx context.Context, roomID, userID string) error {
	err := s.repo.LeaveRoom(ctx, roomID, userID)
	if err != nil {
		return err
	}

	if s.redis != nil {
		_ = s.redis.InvalidateRoomCache(ctx, roomID)
	}

	if s.workerPool != nil {
		s.workerPool.Enqueue(workerpool.AuditEvent{
			EventType: "ROOM_LEFT",
			Severity:  "INFO",
			Payload: map[string]interface{}{
				"room_id": roomID,
				"user_id": userID,
			},
		})
	}

	return nil
}

// GetRoomStatus implementa Cache-Aside con Redis y fallback a PostgreSQL
func (s *Service) GetRoomStatus(ctx context.Context, roomID string) (*ecostreamv1.RoomInfo, error) {
	// 1. Intentar Cache HIT en Redis
	if s.redis != nil {
		if cached, err := s.redis.GetRoomCache(ctx, roomID); err == nil && cached != "" {
			var room ecostreamv1.RoomInfo
			if jsonErr := json.Unmarshal([]byte(cached), &room); jsonErr == nil {
				return &room, nil
			}
		}
	}

	// 2. Cache MISS: Consultar base de datos relacional PostgreSQL
	room, err := s.repo.GetRoomByID(ctx, roomID)
	if err != nil {
		return nil, err
	}

	// 3. Escribir en caché con TTL de 30 segundos
	s.cacheRoom(ctx, room)

	return room, nil
}

// StartMatch cambia el estado a IN_PROGRESS y valida permisos de host
func (s *Service) StartMatch(ctx context.Context, roomID, hostUserID string, fillWithBots bool) (*ecostreamv1.RoomInfo, string, error) {
	room, err := s.repo.StartMatch(ctx, roomID, hostUserID)
	if err != nil {
		return nil, "", err
	}

	// Generar ticket de entrada a simulación para el host
	ticket, err := s.ticketManager.GenerateTicket(room.RoomId, hostUserID, "host", 0, true)
	if err != nil {
		return nil, "", err
	}

	if s.redis != nil {
		_ = s.redis.InvalidateRoomCache(ctx, room.RoomId)
	}

	if s.workerPool != nil {
		s.workerPool.Enqueue(workerpool.AuditEvent{
			EventType: "MATCH_STARTED",
			Severity:  "INFO",
			Payload: map[string]interface{}{
				"room_id":  room.RoomId,
				"host_id":  hostUserID,
				"fill_bot": fillWithBots,
			},
		})
	}

	return room, ticket, nil
}

// ListAvailableRooms obtiene las salas abiertas para el navegador de servidores
func (s *Service) ListAvailableRooms(ctx context.Context, pageSize uint32) ([]*ecostreamv1.RoomInfo, error) {
	return s.repo.ListAvailableRooms(ctx, pageSize)
}

func (s *Service) cacheRoom(ctx context.Context, room *ecostreamv1.RoomInfo) {
	if s.redis == nil || room == nil {
		return
	}
	bytes, err := json.Marshal(room)
	if err != nil {
		return
	}
	if err := s.redis.SetRoomCache(ctx, room.RoomId, string(bytes), 30*time.Second); err != nil {
		log.Printf("[DEBUG] No se pudo guardar room en Redis cache: %v", err)
	}
}
