package matchmaking

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"math/rand"
	"net/http"
	"time"

	"github.com/Makmadon/ecostream-3r/gateway-go/internal/auth"
)

type Service struct {
	db          *sql.DB
	authService *auth.Service
	defaultSim  string
}

func NewService(db *sql.DB, authService *auth.Service, defaultSim string) *Service {
	return &Service{
		db:          db,
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

	if s.db == nil {
		roomTicket := fmt.Sprintf("tkt_mock_%s_%d", claims.UserID, time.Now().Unix())
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"message": "Sala creada exitosamente (modo local/mock)",
			"room": map[string]interface{}{
				"room_id":             "rm_mock_01",
				"room_code":           roomCode,
				"room_name":           req.RoomName,
				"status":              1,
				"max_players":         req.MaxPlayers,
				"simulation_endpoint": s.defaultSim,
			},
			"room_ticket": roomTicket,
		})
		return
	}

	query := `INSERT INTO rooms (room_code, room_name, host_user_id, status, max_players, difficulty_level, simulation_endpoint)
	          VALUES ($1, $2, $3, 1, $4, $5, $6)
	          RETURNING id`
	err = s.db.QueryRow(query, roomCode, req.RoomName, claims.UserID, req.MaxPlayers, req.DifficultyLevel, s.defaultSim).Scan(&roomID)
	if err != nil {
		http.Error(w, fmt.Sprintf("Error creando sala: %v", err), http.StatusInternalServerError)
		return
	}

	// Unir al host a la sala
	_, _ = s.db.Exec(`INSERT INTO room_players (room_id, user_id, selected_role, is_host, is_ready)
	                  VALUES ($1, $2, $3, TRUE, TRUE)`, roomID, claims.UserID, req.SelectedRole)

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

	if s.db == nil {
		roomTicket := fmt.Sprintf("tkt_mock_%s_%d", claims.UserID, time.Now().Unix())
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"message": "Unido a la sala exitosamente (modo local/mock)",
			"room": map[string]interface{}{
				"room_code":           req.RoomCode,
				"simulation_endpoint": s.defaultSim,
			},
			"room_ticket": roomTicket,
		})
		return
	}

	var roomID, roomName, simEndpoint string
	var status, maxPlayers int

	query := `SELECT id, room_name, status, max_players, simulation_endpoint
	          FROM rooms
	          WHERE room_code = $1 AND status IN (1, 2)`
	err = s.db.QueryRow(query, req.RoomCode).Scan(&roomID, &roomName, &status, &maxPlayers, &simEndpoint)
	if err == sql.ErrNoRows {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]interface{}{"success": false, "message": "Sala no encontrada o partida ya finalizada"})
		return
	} else if err != nil {
		http.Error(w, fmt.Sprintf("Error buscando sala: %v", err), http.StatusInternalServerError)
		return
	}

	// Verificar si la sala ya esta llena
	var currentPlayers int
	err = s.db.QueryRow(`SELECT COUNT(*) FROM room_players WHERE room_id = $1`, roomID).Scan(&currentPlayers)
	if err == nil && currentPlayers >= maxPlayers {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusConflict)
		json.NewEncoder(w).Encode(map[string]interface{}{"success": false, "message": "La sala ya alcanzo el maximo de jugadores"})
		return
	}

	// Registrar o actualizar jugador en la sala
	_, err = s.db.Exec(`INSERT INTO room_players (room_id, user_id, selected_role, is_host, is_ready)
	                  VALUES ($1, $2, $3, FALSE, TRUE)
	                  ON CONFLICT (room_id, user_id) DO UPDATE SET selected_role = $3, is_ready = TRUE`,
		roomID, claims.UserID, req.SelectedRole)
	if err != nil {
		http.Error(w, fmt.Sprintf("Error uniendo a sala: %v", err), http.StatusInternalServerError)
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

	if s.db == nil {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"rooms": []map[string]interface{}{
				{
					"room_id":             "rm_mock_01",
					"room_code":           "AGUA-DEMO",
					"room_name":           "Sala Demo Local",
					"status":              1,
					"max_players":         4,
					"difficulty_level":    1,
					"simulation_endpoint": s.defaultSim,
				},
			},
		})
		return
	}

	rows, err := s.db.Query(`SELECT id, room_code, room_name, status, max_players, difficulty_level, simulation_endpoint, created_at
	                         FROM rooms
	                         WHERE status IN (1, 2)
	                         ORDER BY created_at DESC
	                         LIMIT 20`)
	if err != nil {
		http.Error(w, "Error consultando salas", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var rooms []map[string]interface{}
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

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"rooms":   rooms,
	})
}
