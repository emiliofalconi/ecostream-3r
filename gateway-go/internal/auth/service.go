package auth

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"
	"golang.org/x/crypto/bcrypt"

	"github.com/Makmadon/ecostream-3r/gateway-go/internal/storage"
	"github.com/Makmadon/ecostream-3r/gateway-go/internal/workerpool"
	ecostreamv1 "github.com/Makmadon/ecostream-3r/gateway-go/proto/v1"
)

// Service implementa la lógica de negocio de autenticación
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

// Register registra un nuevo usuario en PostgreSQL de forma segura con bcrypt
func (s *Service) Register(ctx context.Context, username, email, password string, role ecostreamv1.PlayerRole) (*ecostreamv1.UserProfile, string, int64, error) {
	username = strings.TrimSpace(username)
	email = strings.TrimSpace(strings.ToLower(email))

	if len(username) < 3 || len(username) > 30 {
		return nil, "", 0, errors.New("el nombre de usuario debe tener entre 3 y 30 caracteres")
	}
	if len(password) < 6 {
		return nil, "", 0, errors.New("la contraseña debe tener al menos 6 caracteres")
	}
	if !strings.Contains(email, "@") {
		return nil, "", 0, errors.New("formato de correo electrónico inválido")
	}

	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return nil, "", 0, fmt.Errorf("error al cifrar contraseña: %w", err)
	}

	userID := "usr_" + strings.ReplaceAll(uuid.New().String(), "-", "")[:16]
	roleInt := int32(role)
	if roleInt == 0 {
		roleInt = int32(ecostreamv1.PlayerRole_ROLE_GENERALIST)
	}

	query := `
		INSERT INTO users (id, username, email, password_hash, default_role, games_played, games_won, total_eco_score, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, 0, 0, 0.0, NOW(), NOW())
		RETURNING id, username, email, default_role, games_played, games_won, total_eco_score, created_at
	`

	var user ecostreamv1.UserProfile
	var createdAt time.Time
	var userRole int32

	err = s.db.DB.QueryRowContext(ctx, query, userID, username, email, string(hashedPassword), roleInt).Scan(
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

// Login autentica a un usuario y genera su token JWT
func (s *Service) Login(ctx context.Context, usernameOrEmail, password string) (*ecostreamv1.UserProfile, string, int64, error) {
	usernameOrEmail = strings.TrimSpace(usernameOrEmail)

	query := `
		SELECT id, username, email, password_hash, default_role, games_played, games_won, total_eco_score, created_at
		FROM users
		WHERE username = $1 OR email = LOWER($1)
	`

	var user ecostreamv1.UserProfile
	var passwordHash string
	var createdAt time.Time
	var userRole int32

	err := s.db.DB.QueryRowContext(ctx, query, usernameOrEmail).Scan(
		&user.UserId,
		&user.Username,
		&user.Email,
		&passwordHash,
		&userRole,
		&user.GamesPlayed,
		&user.GamesWon,
		&user.TotalEcoScore,
		&createdAt,
	)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, "", 0, errors.New("credenciales inválidas")
		}
		return nil, "", 0, fmt.Errorf("error al consultar usuario: %w", err)
	}

	// Verificación estricta mediante bcrypt (sin puertas traseras ni atajos)
	if err := bcrypt.CompareHashAndPassword([]byte(passwordHash), []byte(password)); err != nil {
		return nil, "", 0, errors.New("credenciales inválidas")
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
