package auth

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"
)

// RoomTicketPayload almacena los datos de autorización para entrar al worker de Rust
type RoomTicketPayload struct {
	RoomID   string `json:"room_id"`
	UserID   string `json:"user_id"`
	Username string `json:"username"`
	Role     int32  `json:"role"`
	IsHost   bool   `json:"is_host"`
	Exp      int64  `json:"exp"`
}

// TicketManager genera y valida tickets HMAC de acceso a la simulación en Rust
type TicketManager struct {
	secretKey []byte
	ttl       time.Duration
}

// NewTicketManager inicializa el generador de RoomTickets
func NewTicketManager(secretKey string, ttl time.Duration) *TicketManager {
	if ttl == 0 {
		ttl = 60 * time.Second // TTL por defecto de 60 segundos
	}
	return &TicketManager{
		secretKey: []byte(secretKey),
		ttl:       ttl,
	}
}

// GenerateTicket crea un RoomTicket firmado con HMAC-SHA256
func (t *TicketManager) GenerateTicket(roomID, userID, username string, role int32, isHost bool) (string, error) {
	exp := time.Now().Add(t.ttl).Unix()

	payload := RoomTicketPayload{
		RoomID:   roomID,
		UserID:   userID,
		Username: username,
		Role:     role,
		IsHost:   isHost,
		Exp:      exp,
	}

	payloadBytes, err := json.Marshal(payload)
	if err != nil {
		return "", fmt.Errorf("error al codificar payload de ticket: %w", err)
	}

	b64Payload := base64.RawURLEncoding.EncodeToString(payloadBytes)

	mac := hmac.New(sha256.New, t.secretKey)
	mac.Write([]byte(b64Payload))
	signatureHex := hex.EncodeToString(mac.Sum(nil))

	return fmt.Sprintf("%s.%s", b64Payload, signatureHex), nil
}

// VerifyTicket valida la firma y vigencia del RoomTicket
func (t *TicketManager) VerifyTicket(ticket string) (*RoomTicketPayload, error) {
	parts := strings.Split(ticket, ".")
	if len(parts) != 2 {
		return nil, errors.New("formato de ticket inválido (se esperaba payload.firma)")
	}

	b64Payload := parts[0]
	signatureHex := parts[1]

	mac := hmac.New(sha256.New, t.secretKey)
	mac.Write([]byte(b64Payload))
	expectedSignature := mac.Sum(nil)

	providedSignature, err := hex.DecodeString(signatureHex)
	if err != nil {
		return nil, errors.New("firma hexadecimal inválida")
	}

	if !hmac.Equal(providedSignature, expectedSignature) {
		return nil, errors.New("firma HMAC del ticket no coincide")
	}

	payloadBytes, err := base64.RawURLEncoding.DecodeString(b64Payload)
	if err != nil {
		return nil, fmt.Errorf("error al decodificar payload de ticket: %w", err)
	}

	var payload RoomTicketPayload
	if err := json.Unmarshal(payloadBytes, &payload); err != nil {
		return nil, fmt.Errorf("error al deserializar payload de ticket: %w", err)
	}

	if time.Now().Unix() > payload.Exp {
		return nil, errors.New("el ticket ha expirado")
	}

	return &payload, nil
}
