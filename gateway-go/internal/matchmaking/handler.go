package matchmaking

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"time"

	"github.com/Makmadon/ecostream-3r/gateway-go/internal/auth"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/circuitbreaker"
)

type Service struct {
	db          *sql.DB
	cb          *circuitbreaker.CircuitBreaker
	authService *auth.Service
	defaultSim  string
}

func NewService(db *sql.DB, authService *auth.Service, defaultSim string, cb ...*circuitbreaker.CircuitBreaker) *Service {
	var breaker *circuitbreaker.CircuitBreaker
	if len(cb) > 0 {
		breaker = cb[0]
	}
	return &Service{
		db:          db,
		cb:          breaker,
		authService: authService,
		defaultSim:  defaultSim,
	}
}

type CreateRoomReq struct {
	Token           string `json:"token"`
	RoomName        string `json:"room_name"`
	SelectedRole    int    `json:"selected_role"`
	MaxPlayers      int    `json:"max_players"`
	DifficultyLevel int    `json:"difficulty_level"`
}

type JoinRoomReq struct {
	Token        string `json:"token"`
	RoomCode     string `json:"room_code"`
	SelectedRole int    `json:"selected_role"`
}

func generateRoomCode() string {
	letters := []rune("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
	rand.Seed(time.Now().UnixNano())
	b := make([]rune, 6)
	for i := range b {
		b[i] = letters[rand.Intn(len(letters))]
	}
	return "AGUA-" + string(b[:4])
}

func (s *Service) CreateRoomHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Metodo no permitido", http.StatusMethodNotAllowed)
		return
	}

	var req CreateRoomReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "JSON invalido", http.StatusBadRequest)
		return
	}

	claims, err := s.authService.ValidateToken(req.Token)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(map[string]interface{}{"success": false, "message": "Token JWT invalido"})
		return
	}

	if req.MaxPlayers <= 0 {
		req.MaxPlayers = 4
	}
	if req.DifficultyLevel <= 0 {
		req.DifficultyLevel = 1
	}

	roomCode := generateRoomCode()
	var roomID string

	if s.db == nil || (s.cb != nil && s.cb.State() == circuitbreaker.StateOpen) {
		roomTicket := fmt.Sprintf("tkt_mock_%s_%d", claims.UserID, time.Now().Unix())
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"message": "Sala creada exitosamente (modo degradado / Circuit Breaker activo)",
			"room": map[string]interface{}{
				"room_id":             "rm_mock_01",
				"room_code":           roomCode,
				"room_name":           req.RoomName,
				"status":              1,
				"max_players":         req.MaxPlayers,
				"simulation_endpoint": s.defaultSim,
			},
			"room_ticket": roomTicket,
			"source":      "circuit_breaker_degraded_mode",
		})
		return
	}

	createFunc := func() error {
		ctx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
		defer cancel()

		query := `INSERT INTO rooms (room_code, room_name, host_user_id, status, max_players, difficulty_level, simulation_endpoint)
		          VALUES ($1, $2, $3, 1, $4, $5, $6)
		          RETURNING id`
		err := s.db.QueryRowContext(ctx, query, roomCode, req.RoomName, claims.UserID, req.MaxPlayers, req.DifficultyLevel, s.defaultSim).Scan(&roomID)
		if err != nil {
			return err
		}

		// Unir al host a la sala
		_, err = s.db.ExecContext(ctx, `INSERT INTO room_players (room_id, user_id, selected_role, is_host, is_ready)
		                  VALUES ($1, $2, $3, TRUE, TRUE)`, roomID, claims.UserID, req.SelectedRole)
		return err
	}

	if s.cb != nil {
		err = s.cb.Execute(createFunc)
	} else {
		err = createFunc()
	}

	if err != nil {
		log.Printf("[MATCHMAKING WARN] Fallo al crear sala en DB (%v), recurriendo a fallback resiliente", err)
		roomTicket := fmt.Sprintf("tkt_fallback_%s_%d", claims.UserID, time.Now().Unix())
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"message": "Sala creada en modo recuperativo de contingencia",
			"room": map[string]interface{}{
				"room_id":             "rm_fb_" + roomCode,
				"room_code":           roomCode,
				"room_name":           req.RoomName,
				"status":              1,
				"max_players":         req.MaxPlayers,
				"simulation_endpoint": s.defaultSim,
			},
			"room_ticket": roomTicket,
			"source":      "circuit_breaker_degraded_mode",
		})
		return
	}

	roomTicket := fmt.Sprintf("tkt_%s_%s_%d", roomID, claims.UserID, time.Now().Unix())

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "Sala creada exitosamente",
		"room": map[string]interface{}{
			"room_id":             roomID,
			"room_code":           roomCode,
			"room_name":           req.RoomName,
			"status":              1,
			"max_players":         req.MaxPlayers,
			"simulation_endpoint": s.defaultSim,
		},
		"room_ticket": roomTicket,
	})
}

func (s *Service) JoinRoomHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Metodo no permitido", http.StatusMethodNotAllowed)
		return
	}

	var req JoinRoomReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "JSON invalido", http.StatusBadRequest)
		return
	}

	claims, err := s.authService.ValidateToken(req.Token)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(map[string]interface{}{"success": false, "message": "Token JWT invalido"})
		return
	}

	if s.db == nil || (s.cb != nil && s.cb.State() == circuitbreaker.StateOpen) {
		roomTicket := fmt.Sprintf("tkt_mock_%s_%d", claims.UserID, time.Now().Unix())
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"message": "Unido a la sala exitosamente (modo degradado / Circuit Breaker activo)",
			"room": map[string]interface{}{
				"room_code":           req.RoomCode,
				"simulation_endpoint": s.defaultSim,
			},
			"room_ticket": roomTicket,
			"source":      "circuit_breaker_degraded_mode",
		})
		return
	}

	var roomID, roomName, simEndpoint string
	var status, maxPlayers int

	joinFunc := func() error {
		ctx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
		defer cancel()

		query := `SELECT id, room_name, status, max_players, simulation_endpoint
		          FROM rooms
		          WHERE room_code = $1 AND status IN (1, 2)`
		err := s.db.QueryRowContext(ctx, query, req.RoomCode).Scan(&roomID, &roomName, &status, &maxPlayers, &simEndpoint)
		if err != nil {
			return err
		}

		// Verificar si la sala ya esta llena
		var currentPlayers int
		err = s.db.QueryRowContext(ctx, `SELECT COUNT(*) FROM room_players WHERE room_id = $1`, roomID).Scan(&currentPlayers)
		if err == nil && currentPlayers >= maxPlayers {
			return fmt.Errorf("ROOM_FULL")
		}

		// Registrar o actualizar jugador en la sala
		_, err = s.db.ExecContext(ctx, `INSERT INTO room_players (room_id, user_id, selected_role, is_host, is_ready)
		                  VALUES ($1, $2, $3, FALSE, TRUE)
		                  ON CONFLICT (room_id, user_id) DO UPDATE SET selected_role = $3, is_ready = TRUE`,
			roomID, claims.UserID, req.SelectedRole)
		return err
	}

	if s.cb != nil {
		err = s.cb.Execute(joinFunc)
	} else {
		err = joinFunc()
	}

	if err == sql.ErrNoRows {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]interface{}{"success": false, "message": "Sala no encontrada o partida ya finalizada"})
		return
	} else if err != nil && err.Error() == "ROOM_FULL" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusConflict)
		json.NewEncoder(w).Encode(map[string]interface{}{"success": false, "message": "La sala ya alcanzo el maximo de jugadores"})
		return
	} else if err != nil {
		log.Printf("[JOIN WARN] Error DB al unirse a sala (%v), respondiendo con fallback", err)
		roomTicket := fmt.Sprintf("tkt_mock_%s_%d", claims.UserID, time.Now().Unix())
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"message": "Unido a la sala en modo contingencia",
			"room": map[string]interface{}{
				"room_code":           req.RoomCode,
				"simulation_endpoint": s.defaultSim,
			},
			"room_ticket": roomTicket,
			"source":      "circuit_breaker_degraded_mode",
		})
		return
	}

	roomTicket := fmt.Sprintf("tkt_%s_%s_%d", roomID, claims.UserID, time.Now().Unix())

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "Unido a la sala exitosamente",
		"room": map[string]interface{}{
			"room_id":             roomID,
			"room_code":           req.RoomCode,
			"room_name":           roomName,
			"status":              status,
			"max_players":         maxPlayers,
			"simulation_endpoint": simEndpoint,
		},
		"room_ticket": roomTicket,
	})
}

func (s *Service) ListRoomsHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Metodo no permitido", http.StatusMethodNotAllowed)
		return
	}

	degradedRooms := []map[string]interface{}{
		{
			"room_id":             "rm_mock_01",
			"room_code":           "AGUA-DEMO",
			"room_name":           "Sala Demo Local",
			"status":              1,
			"max_players":         4,
			"difficulty_level":    1,
			"simulation_endpoint": s.defaultSim,
		},
	}

	if s.db == nil || (s.cb != nil && s.cb.State() == circuitbreaker.StateOpen) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"rooms":   degradedRooms,
			"source":  "circuit_breaker_degraded_mode",
		})
		return
	}

	var rooms []map[string]interface{}
	listFunc := func() error {
		ctx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
		defer cancel()

		rows, err := s.db.QueryContext(ctx, `SELECT id, room_code, room_name, status, max_players, difficulty_level, simulation_endpoint, created_at
		                         FROM rooms
		                         WHERE status IN (1, 2)
		                         ORDER BY created_at DESC
		                         LIMIT 20`)
		if err != nil {
			return err
		}
		defer rows.Close()

		for rows.Next() {
			var id, code, name, sim string
			var status, max, diff int
			var created time.Time
			if err := rows.Scan(&id, &code, &name, &status, &max, &diff, &sim, &created); err == nil {
				rooms = append(rooms, map[string]interface{}{
					"room_id":             id,
					"room_code":           code,
					"room_name":           name,
					"status":              status,
					"max_players":         max,
					"difficulty_level":    diff,
					"simulation_endpoint": sim,
					"created_at":          created,
				})
			}
		}
		return rows.Err()
	}

	var err error
	if s.cb != nil {
		err = s.cb.Execute(listFunc)
	} else {
		err = listFunc()
	}

	if err != nil {
		log.Printf("[ROOMS WARN] Error consultando salas (%v), entregando salas fallback", err)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"rooms":   degradedRooms,
			"source":  "circuit_breaker_degraded_mode",
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"rooms":   rooms,
	})
}
