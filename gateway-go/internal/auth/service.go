package auth

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"

	"github.com/Makmadon/ecostream-3r/gateway-go/internal/storage"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/workerpool"
	ecostreamv1 "github.com/Makmadon/ecostream-3r/gateway-go/proto/v1"
)

// Service implementa la lógica de negocio de autenticación y gestión de jugadores
type Service struct {
	db         *storage.PostgresDB
	jwtManager *JWTManager
	workerPool *workerpool.WorkerPool
}

// NewService crea una nueva instancia de AuthService
func NewService(db *storage.PostgresDB, jwtManager *JWTManager, workerPool *workerpool.WorkerPool) *Service {
	return &Service{
		db:         db,
		jwtManager: jwtManager,
		workerPool: workerPool,
	}
}

// Register registra un nuevo usuario en PostgreSQL por nombre de usuario
func (s *Service) Register(ctx context.Context, username, email string, role ecostreamv1.PlayerRole) (*ecostreamv1.UserProfile, string, int64, error) {
	username = strings.TrimSpace(username)
	email = strings.TrimSpace(strings.ToLower(email))

	if len(username) < 2 || len(username) > 30 {
		return nil, "", 0, errors.New("el nombre de usuario debe tener entre 2 y 30 caracteres")
	}
	if email == "" {
		email = fmt.Sprintf("%s@ecostream.local", strings.ToLower(username))
	} else if !strings.Contains(email, "@") {
		return nil, "", 0, errors.New("formato de correo electrónico inválido")
	}

	userID := "usr_" + strings.ReplaceAll(uuid.New().String(), "-", "")[:16]
	roleInt := int32(role)
	if roleInt == 0 {
		roleInt = int32(ecostreamv1.PlayerRole_ROLE_GENERALIST)
	}

	query := `
		INSERT INTO users (id, username, email, default_role, games_played, games_won, total_eco_score, created_at, updated_at)
		VALUES ($1, $2, $3, $4, 0, 0, 0.0, NOW(), NOW())
		RETURNING id, username, email, default_role, games_played, games_won, total_eco_score, created_at
	`

	var user ecostreamv1.UserProfile
	var createdAt time.Time
	var userRole int32

	err := s.db.DB.QueryRowContext(ctx, query, userID, username, email, roleInt).Scan(
		&user.UserId,
		&user.Username,
		&user.Email,
		&userRole,
		&user.GamesPlayed,
		&user.GamesWon,
		&user.TotalEcoScore,
		&createdAt,
	)
	if err != nil {
		if strings.Contains(err.Error(), "duplicate key") || strings.Contains(err.Error(), "unique constraint") {
			return nil, "", 0, errors.New("el usuario o correo electrónico ya se encuentra registrado")
		}
		return nil, "", 0, fmt.Errorf("error al registrar usuario en base de datos: %w", err)
	}

	user.DefaultRole = ecostreamv1.PlayerRole(userRole)
	user.CreatedAt = createdAt.Format(time.RFC3339)

	token, expiresAt, err := s.jwtManager.GenerateToken(user.UserId, user.Username, int32(user.DefaultRole))
	if err != nil {
		return nil, "", 0, err
	}

	if s.workerPool != nil {
		s.workerPool.Enqueue(workerpool.AuditEvent{
			EventType: "USER_REGISTERED",
			Severity:  "INFO",
			Payload: map[string]interface{}{
				"user_id":  user.UserId,
				"username": user.Username,
			},
		})
	}

	return &user, token, expiresAt, nil
}

// Login autentica a un usuario directamente por su nombre de usuario (sin contraseñas)
func (s *Service) Login(ctx context.Context, username string) (*ecostreamv1.UserProfile, string, int64, error) {
	username = strings.TrimSpace(username)
	if username == "" {
		return nil, "", 0, errors.New("nombre de usuario requerido")
	}

	query := `
		SELECT id, username, email, default_role, games_played, games_won, total_eco_score, created_at
		FROM users
		WHERE username = $1 OR email = LOWER($1)
	`

	var user ecostreamv1.UserProfile
	var createdAt time.Time
	var userRole int32

	err := s.db.DB.QueryRowContext(ctx, query, username).Scan(
		&user.UserId,
		&user.Username,
		&user.Email,
		&userRole,
		&user.GamesPlayed,
		&user.GamesWon,
		&user.TotalEcoScore,
		&createdAt,
	)

	// Si el usuario no existe, auto-registrarlo de inmediato como jugador sin fricción
	if errors.Is(err, sql.ErrNoRows) {
		return s.autoRegisterGuest(ctx, username)
	} else if err != nil {
		return nil, "", 0, fmt.Errorf("error al consultar usuario: %w", err)
	}

	user.DefaultRole = ecostreamv1.PlayerRole(userRole)
	user.CreatedAt = createdAt.Format(time.RFC3339)

	token, expiresAt, err := s.jwtManager.GenerateToken(user.UserId, user.Username, int32(user.DefaultRole))
	if err != nil {
		return nil, "", 0, err
	}

	if s.workerPool != nil {
		s.workerPool.Enqueue(workerpool.AuditEvent{
			EventType: "USER_LOGIN_SUCCESS",
			Severity:  "INFO",
			Payload: map[string]interface{}{
				"user_id":  user.UserId,
				"username": user.Username,
			},
		})
	}

	return &user, token, expiresAt, nil
}

func (s *Service) autoRegisterGuest(ctx context.Context, username string) (*ecostreamv1.UserProfile, string, int64, error) {
	if len(username) < 2 || len(username) > 30 {
		return nil, "", 0, errors.New("el nombre de usuario debe tener entre 2 y 30 caracteres")
	}

	userID := "usr_" + strings.ReplaceAll(uuid.New().String(), "-", "")[:16]
	cleanName := strings.Map(func(r rune) rune {
		if (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') || r == '_' || r == '-' {
			return r
		}
		return '_'
	}, username)
	email := fmt.Sprintf("%s_%s@ecostream.local", strings.ToLower(cleanName), userID[4:10])
	roleInt := int32(ecostreamv1.PlayerRole_ROLE_GENERALIST)

	insertQuery := `
		INSERT INTO users (id, username, email, default_role, games_played, games_won, total_eco_score, created_at, updated_at)
		VALUES ($1, $2, $3, $4, 0, 0, 0.0, NOW(), NOW())
		RETURNING id, username, email, default_role, games_played, games_won, total_eco_score, created_at
	`

	var user ecostreamv1.UserProfile
	var createdAt time.Time
	var userRole int32

	err := s.db.DB.QueryRowContext(ctx, insertQuery, userID, username, email, roleInt).Scan(
		&user.UserId,
		&user.Username,
		&user.Email,
		&userRole,
		&user.GamesPlayed,
		&user.GamesWon,
		&user.TotalEcoScore,
		&createdAt,
	)
	if err != nil {
		// En caso de concurrencia donde el usuario fue creado milisegundos antes
		var retryUser ecostreamv1.UserProfile
		selectQuery := `SELECT id, username, email, default_role, games_played, games_won, total_eco_score, created_at FROM users WHERE username = $1`
		if retryErr := s.db.DB.QueryRowContext(ctx, selectQuery, username).Scan(
			&retryUser.UserId,
			&retryUser.Username,
			&retryUser.Email,
			&userRole,
			&retryUser.GamesPlayed,
			&retryUser.GamesWon,
			&retryUser.TotalEcoScore,
			&createdAt,
		); retryErr == nil {
			retryUser.DefaultRole = ecostreamv1.PlayerRole(userRole)
			retryUser.CreatedAt = createdAt.Format(time.RFC3339)
			token, expiresAt, tErr := s.jwtManager.GenerateToken(retryUser.UserId, retryUser.Username, int32(retryUser.DefaultRole))
			if tErr == nil {
				return &retryUser, token, expiresAt, nil
			}
		}
		return nil, "", 0, fmt.Errorf("error al registrar jugador automático: %w", err)
	}

	user.DefaultRole = ecostreamv1.PlayerRole(userRole)
	user.CreatedAt = createdAt.Format(time.RFC3339)

	token, expiresAt, err := s.jwtManager.GenerateToken(user.UserId, user.Username, int32(user.DefaultRole))
	if err != nil {
		return nil, "", 0, err
	}

	if s.workerPool != nil {
		s.workerPool.Enqueue(workerpool.AuditEvent{
			EventType: "USER_AUTO_REGISTERED",
			Severity:  "INFO",
			Payload: map[string]interface{}{
				"user_id":  user.UserId,
				"username": user.Username,
			},
		})
	}

	return &user, token, expiresAt, nil
}

// VerifyToken valida un token JWT existente
func (s *Service) VerifyToken(tokenString string) (*UserClaims, error) {
	return s.jwtManager.VerifyToken(tokenString)
}

// GetProfile obtiene el perfil de un usuario por su ID
func (s *Service) GetProfile(ctx context.Context, userID string) (*ecostreamv1.UserProfile, error) {
	query := `
		SELECT id, username, email, default_role, games_played, games_won, total_eco_score, created_at
		FROM users
		WHERE id = $1
	`

	var user ecostreamv1.UserProfile
	var createdAt time.Time
	var userRole int32

	err := s.db.DB.QueryRowContext(ctx, query, userID).Scan(
		&user.UserId,
		&user.Username,
		&user.Email,
		&userRole,
		&user.GamesPlayed,
		&user.GamesWon,
		&user.TotalEcoScore,
		&createdAt,
	)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, errors.New("usuario no encontrado")
		}
		return nil, fmt.Errorf("error al consultar perfil: %w", err)
	}

	user.DefaultRole = ecostreamv1.PlayerRole(userRole)
	user.CreatedAt = createdAt.Format(time.RFC3339)

	return &user, nil
}
