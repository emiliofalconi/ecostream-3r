package auth

import (
	"errors"
	"fmt"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

// UserClaims define los claims contenidos en el JWT de sesión del jugador
type UserClaims struct {
	UserID   string `json:"user_id"`
	Username string `json:"username"`
	Role     int32  `json:"role"`
	jwt.RegisteredClaims
}

// JWTManager coordina la creación y validación de tokens JWT HS256
type JWTManager struct {
	secretKey     []byte
	tokenDuration time.Duration
}

// NewJWTManager inicializa el gestor de JWT
func NewJWTManager(secretKey string, duration time.Duration) *JWTManager {
	return &JWTManager{
		secretKey:     []byte(secretKey),
		tokenDuration: duration,
	}
}

// GenerateToken genera un JWT firmado con los datos del usuario
func (m *JWTManager) GenerateToken(userID string, username string, role int32) (string, int64, error) {
	now := time.Now()
	expiresAt := now.Add(m.tokenDuration)

	claims := &UserClaims{
		UserID:   userID,
		Username: username,
		Role:     role,
		RegisteredClaims: jwt.RegisteredClaims{
			Issuer:    "ecostream-3r",
			Subject:   userID,
			IssuedAt:  jwt.NewNumericDate(now),
			ExpiresAt: jwt.NewNumericDate(expiresAt),
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, err := token.SignedString(m.secretKey)
	if err != nil {
		return "", 0, fmt.Errorf("error al firmar JWT: %w", err)
	}

	return tokenString, expiresAt.Unix(), nil
}

// VerifyToken valida la firma y expiración del JWT y retorna los claims
func (m *JWTManager) VerifyToken(tokenString string) (*UserClaims, error) {
	token, err := jwt.ParseWithClaims(
		tokenString,
		&UserClaims{},
		func(token *jwt.Token) (interface{}, error) {
			if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, fmt.Errorf("método de firma inesperado: %v", token.Header["alg"])
			}
			return m.secretKey, nil
		},
	)

	if err != nil {
		return nil, fmt.Errorf("token inválido: %w", err)
	}

	claims, ok := token.Claims.(*UserClaims)
	if !ok || !token.Valid {
		return nil, errors.New("claims de token inválidos o expirados")
	}

	return claims, nil
}
