package auth

import (
	"testing"
	"time"
)

func TestJWTGenerationAndVerification(t *testing.T) {
	secret := "test_super_secret_jwt_key_12345"
	jwtMgr := NewJWTManager(secret, 1*time.Hour)

	token, exp, err := jwtMgr.GenerateToken("usr_test_123", "AquaHero", 1)
	if err != nil {
		t.Fatalf("Error al generar token: %v", err)
	}

	if token == "" {
		t.Fatal("Token generado no debe ser vacío")
	}

	if exp <= time.Now().Unix() {
		t.Fatal("La expiración del token debe estar en el futuro")
	}

	// Verificar token válido
	claims, err := jwtMgr.VerifyToken(token)
	if err != nil {
		t.Fatalf("Fallo al verificar token válido: %v", err)
	}

	if claims.UserID != "usr_test_123" {
		t.Errorf("UserID esperado usr_test_123, obtenido %s", claims.UserID)
	}

	if claims.Username != "AquaHero" {
		t.Errorf("Username esperado AquaHero, obtenido %s", claims.Username)
	}

	if claims.Role != 1 {
		t.Errorf("Role esperado 1, obtenido %d", claims.Role)
	}

	// Verificar token con firma inválida
	otherMgr := NewJWTManager("clave_totalmente_distinta", 1*time.Hour)
	_, err = otherMgr.VerifyToken(token)
	if err == nil {
		t.Fatal("Se esperaba error al verificar token con firma inválida")
	}
}

func TestJWTExpired(t *testing.T) {
	secret := "test_super_secret_jwt_key_12345"
	jwtMgr := NewJWTManager(secret, -1*time.Hour) // Ya expirado

	token, _, err := jwtMgr.GenerateToken("usr_test_exp", "AquaHero", 1)
	if err != nil {
		t.Fatalf("Error al generar token: %v", err)
	}

	_, err = jwtMgr.VerifyToken(token)
	if err == nil {
		t.Fatal("Se esperaba error al verificar token expirado")
	}
}
