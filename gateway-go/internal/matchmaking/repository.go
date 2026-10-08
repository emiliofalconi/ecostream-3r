package matchmaking

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"

	"github.com/Makmadon/ecostream-3r/gateway-go/internal/storage"
	ecostreamv1 "github.com/Makmadon/ecostream-3r/gateway-go/proto/v1"
)

var (
	ErrRoomNotFound = errors.New("sala no encontrada")
	ErrRoomFull     = errors.New("la sala ha alcanzado el límite máximo de jugadores")
	ErrNotInWaiting = errors.New("la partida ya ha comenzado o ha finalizado")
	ErrNotHost      = errors.New("solo el anfitrión de la sala puede realizar esta acción")
)

// Repository gestiona la persistencia y consultas transaccionales de salas
type Repository struct {
	db *storage.PostgresDB
}

// NewRepository inicializa el repositorio de matchmaking
func NewRepository(db *storage.PostgresDB) *Repository {
	return &Repository{db: db}
}

// CreateRoom inserta una nueva sala y registra al anfitrión en una transacción atómica
func (r *Repository) CreateRoom(ctx context.Context, room *ecostreamv1.RoomInfo, hostID, hostUsername string, hostRole ecostreamv1.PlayerRole) error {
	tx, err := r.db.DB.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("error al iniciar transacción: %w", err)
	}
	defer tx.Rollback()

	queryRoom := `
		INSERT INTO rooms (id, room_code, room_name, host_user_id, status, current_players, max_players, difficulty_level, simulation_endpoint, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, 1, $6, $7, $8, NOW(), NOW())
	`
	_, err = tx.ExecContext(ctx, queryRoom,
		room.RoomId,
		room.RoomCode,
		room.RoomName,
		hostID,
		int32(room.Status),
		room.MaxPlayers,
		room.DifficultyLevel,
		room.SimulationEndpoint,
	)
	if err != nil {
		return fmt.Errorf("error al insertar sala: %w", err)
	}

	queryPlayer := `
		INSERT INTO room_players (room_id, user_id, selected_role, is_host, is_ready, is_bot, joined_at)
		VALUES ($1, $2, $3, TRUE, TRUE, FALSE, NOW())
	`
	_, err = tx.ExecContext(ctx, queryPlayer, room.RoomId, hostID, int32(hostRole))
	if err != nil {
		return fmt.Errorf("error al insertar anfitrión en la sala: %w", err)
	}

	return tx.Commit()
}

// JoinRoomAtomic ejecuta una reserva atómica de cupo y asocia al jugador
func (r *Repository) JoinRoomAtomic(ctx context.Context, roomCode string, userID, username string, role ecostreamv1.PlayerRole) (*ecostreamv1.RoomInfo, error) {
	tx, err := r.db.DB.BeginTx(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("error al iniciar transacción: %w", err)
	}
	defer tx.Rollback()

	// Actualización atómica de cupo con condición estricta
	updateQuery := `
		UPDATE rooms
		SET current_players = current_players + 1, updated_at = NOW()
		WHERE room_code = $1 AND current_players < max_players AND status = 1
		RETURNING id, room_code, room_name, status, max_players, difficulty_level, simulation_endpoint, created_at
	`

	var room ecostreamv1.RoomInfo
	var roomStatus int32
	var createdAt time.Time

	err = tx.QueryRowContext(ctx, updateQuery, roomCode).Scan(
		&room.RoomId,
		&room.RoomCode,
		&room.RoomName,
		&roomStatus,
		&room.MaxPlayers,
		&room.DifficultyLevel,
		&room.SimulationEndpoint,
		&createdAt,
	)

	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			// Diagnosticar razón exacta del fallo
			var curPlayers, maxPlayers, status int
			checkErr := tx.QueryRowContext(ctx, `SELECT current_players, max_players, status FROM rooms WHERE room_code = $1`, roomCode).Scan(&curPlayers, &maxPlayers, &status)
			if errors.Is(checkErr, sql.ErrNoRows) {
				return nil, ErrRoomNotFound
			}
			if status != 1 {
				return nil, ErrNotInWaiting
			}
			if curPlayers >= maxPlayers {
				return nil, ErrRoomFull
			}
			return nil, fmt.Errorf("no fue posible unirse a la sala")
		}
		return nil, fmt.Errorf("error al actualizar cupo en la sala: %w", err)
	}

	room.Status = ecostreamv1.RoomStatus(roomStatus)
	room.CreatedAtUnix = createdAt.Unix()

	// Insertar al jugador en room_players
	insertPlayer := `
		INSERT INTO room_players (room_id, user_id, selected_role, is_host, is_ready, is_bot, joined_at)
		VALUES ($1, $2, $3, FALSE, TRUE, FALSE, NOW())
		ON CONFLICT (room_id, user_id) DO UPDATE SET selected_role = EXCLUDED.selected_role
	`
	_, err = tx.ExecContext(ctx, insertPlayer, room.RoomId, userID, int32(role))
	if err != nil {
		return nil, fmt.Errorf("error al registrar jugador en la sala: %w", err)
	}

	if err := tx.Commit(); err != nil {
		return nil, fmt.Errorf("error al confirmar transacción de unión: %w", err)
	}

	// Obtener lista completa de jugadores de la sala
	players, err := r.GetRoomPlayers(ctx, room.RoomId)
	if err == nil {
		room.Players = players
	}

	return &room, nil
}

// GetRoomPlayers retorna los jugadores inscritos en una sala
func (r *Repository) GetRoomPlayers(ctx context.Context, roomID string) ([]*ecostreamv1.PlayerSlot, error) {
	query := `
		SELECT rp.user_id, u.username, rp.selected_role, rp.is_host, rp.is_ready, rp.is_bot
		FROM room_players rp
		JOIN users u ON rp.user_id = u.id
		WHERE rp.room_id = $1
		ORDER BY rp.joined_at ASC
	`
	rows, err := r.db.DB.QueryContext(ctx, query, roomID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var players []*ecostreamv1.PlayerSlot
	for rows.Next() {
		var p ecostreamv1.PlayerSlot
		var roleInt int32
		if err := rows.Scan(&p.UserId, &p.Username, &roleInt, &p.IsHost, &p.IsReady, &p.IsBot); err != nil {
			continue
		}
		p.SelectedRole = ecostreamv1.PlayerRole(roleInt)
		players = append(players, &p)
	}
	return players, nil
}

// GetRoomByID obtiene los datos y jugadores de una sala por su ID
func (r *Repository) GetRoomByID(ctx context.Context, roomID string) (*ecostreamv1.RoomInfo, error) {
	query := `
		SELECT id, room_code, room_name, status, max_players, difficulty_level, simulation_endpoint, created_at
		FROM rooms
		WHERE id = $1
	`
	var room ecostreamv1.RoomInfo
	var statusInt int32
	var createdAt time.Time

	err := r.db.DB.QueryRowContext(ctx, query, roomID).Scan(
		&room.RoomId,
		&room.RoomCode,
		&room.RoomName,
		&statusInt,
		&room.MaxPlayers,
		&room.DifficultyLevel,
		&room.SimulationEndpoint,
		&createdAt,
	)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, ErrRoomNotFound
		}
		return nil, err
	}

	room.Status = ecostreamv1.RoomStatus(statusInt)
	room.CreatedAtUnix = createdAt.Unix()

	players, err := r.GetRoomPlayers(ctx, room.RoomId)
	if err == nil {
		room.Players = players
	}

	return &room, nil
}

// GetRoomByCode obtiene los datos de una sala por su código amigable
func (r *Repository) GetRoomByCode(ctx context.Context, roomCode string) (*ecostreamv1.RoomInfo, error) {
	query := `
		SELECT id, room_code, room_name, status, max_players, difficulty_level, simulation_endpoint, created_at
		FROM rooms
		WHERE room_code = $1
	`
	var room ecostreamv1.RoomInfo
	var statusInt int32
	var createdAt time.Time

	err := r.db.DB.QueryRowContext(ctx, query, roomCode).Scan(
		&room.RoomId,
		&room.RoomCode,
		&room.RoomName,
		&statusInt,
		&room.MaxPlayers,
		&room.DifficultyLevel,
		&room.SimulationEndpoint,
		&createdAt,
	)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, ErrRoomNotFound
		}
		return nil, err
	}

	room.Status = ecostreamv1.RoomStatus(statusInt)
	room.CreatedAtUnix = createdAt.Unix()

	players, err := r.GetRoomPlayers(ctx, room.RoomId)
	if err == nil {
		room.Players = players
	}

	return &room, nil
}

// FindAvailableRoom busca la sala con mayor ocupación disponible para matchmaking rápido
func (r *Repository) FindAvailableRoom(ctx context.Context) (string, error) {
	query := `
		SELECT room_code
		FROM rooms
		WHERE status = 1 AND current_players < max_players
		ORDER BY current_players DESC, created_at ASC
		LIMIT 1
	`
	var roomCode string
	err := r.db.DB.QueryRowContext(ctx, query).Scan(&roomCode)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return "", ErrRoomNotFound
		}
		return "", err
	}
	return roomCode, nil
}

// LeaveRoom remueve al jugador y actualiza la cantidad de jugadores
func (r *Repository) LeaveRoom(ctx context.Context, roomID, userID string) error {
	tx, err := r.db.DB.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer tx.Rollback()

	// Eliminar de room_players
	res, err := tx.ExecContext(ctx, `DELETE FROM room_players WHERE room_id = $1 AND user_id = $2`, roomID, userID)
	if err != nil {
		return err
	}
	rowsAffected, _ := res.RowsAffected()
	if rowsAffected == 0 {
		return nil // No estaba en la sala
	}

	// Decrementar current_players
	updateQuery := `
		UPDATE rooms
		SET current_players = GREATEST(0, current_players - 1), updated_at = NOW()
		WHERE id = $1
		RETURNING current_players
	`
	var remaining int
	if err := tx.QueryRowContext(ctx, updateQuery, roomID).Scan(&remaining); err != nil {
		return err
	}

	if remaining == 0 {
		// Si quedó vacía, marcar como terminada
		tx.ExecContext(ctx, `UPDATE rooms SET status = 4, updated_at = NOW() WHERE id = $1`, roomID)
	}

	return tx.Commit()
}

// StartMatch actualiza el estado de la sala a IN_PROGRESS si quien lo solicita es el host
func (r *Repository) StartMatch(ctx context.Context, roomID, hostUserID string) (*ecostreamv1.RoomInfo, error) {
	query := `
		UPDATE rooms
		SET status = 3, updated_at = NOW()
		WHERE id = $1 AND host_user_id = $2 AND status = 1
		RETURNING id, room_code, room_name, status, max_players, difficulty_level, simulation_endpoint, created_at
	`
	var room ecostreamv1.RoomInfo
	var statusInt int32
	var createdAt time.Time

	err := r.db.DB.QueryRowContext(ctx, query, roomID, hostUserID).Scan(
		&room.RoomId,
		&room.RoomCode,
		&room.RoomName,
		&statusInt,
		&room.MaxPlayers,
		&room.DifficultyLevel,
		&room.SimulationEndpoint,
		&createdAt,
	)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, errors.New("no autorizado o la sala no está en espera")
		}
		return nil, err
	}

	room.Status = ecostreamv1.RoomStatus(statusInt)
	room.CreatedAtUnix = createdAt.Unix()

	players, _ := r.GetRoomPlayers(ctx, room.RoomId)
	room.Players = players

	return &room, nil
}

// ListAvailableRooms retorna la lista de salas abiertas
func (r *Repository) ListAvailableRooms(ctx context.Context, pageSize uint32) ([]*ecostreamv1.RoomInfo, error) {
	if pageSize == 0 || pageSize > 50 {
		pageSize = 20
	}

	query := `
		SELECT id, room_code, room_name, status, max_players, difficulty_level, simulation_endpoint, created_at
		FROM rooms
		WHERE status = 1 AND current_players < max_players
		ORDER BY created_at DESC
		LIMIT $1
	`
	rows, err := r.db.DB.QueryContext(ctx, query, pageSize)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var rooms []*ecostreamv1.RoomInfo
	for rows.Next() {
		var room ecostreamv1.RoomInfo
		var statusInt int32
		var createdAt time.Time

		if err := rows.Scan(
			&room.RoomId,
			&room.RoomCode,
			&room.RoomName,
			&statusInt,
			&room.MaxPlayers,
			&room.DifficultyLevel,
			&room.SimulationEndpoint,
			&createdAt,
		); err != nil {
			continue
		}

		room.Status = ecostreamv1.RoomStatus(statusInt)
		room.CreatedAtUnix = createdAt.Unix()

		players, _ := r.GetRoomPlayers(ctx, room.RoomId)
		room.Players = players

		rooms = append(rooms, &room)
	}

	return rooms, nil
}
