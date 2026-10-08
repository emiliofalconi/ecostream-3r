package auth

import (
	"strings"
	"testing"
	"time"
)

func TestRoomTicketGenerationAndVerification(t *testing.T) {
	secret := "test_hmac_ticket_secret_key"
	tm := NewTicketManager(secret, 60*time.Second)

	ticket, err := tm.GenerateTicket("rm_agua_01", "usr_100", "EcoLeader", 2, true)
	if err != nil {
		t.Fatalf("Error al generar RoomTicket: %v", err)
	}

	if !strings.Contains(ticket, ".") {
		t.Fatalf("El ticket debe tener formato payload.firma: %s", ticket)
	}

	// Validación exitosa
	payload, err := tm.VerifyTicket(ticket)
	if err != nil {
		t.Fatalf("Fallo al verificar ticket legítimo: %v", err)
	}

	if payload.RoomID != "rm_agua_01" || payload.UserID != "usr_100" || !payload.IsHost {
		t.Errorf("Campos de payload no coinciden: %+v", payload)
	}

	// Validación con clave errónea
	badTM := NewTicketManager("otra_clave_distinta", 60*time.Second)
	_, err = badTM.VerifyTicket(ticket)
	if err == nil {
		t.Fatal("Se esperaba rechazo por firma HMAC incorrecta")
	}

	// Validación de ticket alterado (tampering)
	tamperedTicket := "eyJyb29tX2lkIjoiZXZpbCJ9." + strings.Split(ticket, ".")[1]
	_, err = tm.VerifyTicket(tamperedTicket)
	if err == nil {
		t.Fatal("Se esperaba rechazo por payload manipulado")
	}
}

func TestRoomTicketExpired(t *testing.T) {
	secret := "test_hmac_ticket_secret_key"
	tm := NewTicketManager(secret, -5*time.Second) // Ya expirado

	ticket, err := tm.GenerateTicket("rm_agua_01", "usr_100", "EcoLeader", 2, true)
	if err != nil {
		t.Fatalf("Error al generar ticket: %v", err)
	}

	_, err = tm.VerifyTicket(ticket)
	if err == nil {
		t.Fatal("Se esperaba error por ticket expirado")
	}
}
