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

func (s *Service) ListRoomsHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Metodo no permitido", http.StatusMethodNotAllowed)
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
