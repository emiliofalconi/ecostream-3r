package circuitbreaker

import (
	"errors"
	"sync/atomic"
	"testing"
	"time"
)

func TestCircuitBreaker_SuccessKeepsClosed(t *testing.T) {
	cb := New("test-cb", 3, 100*time.Millisecond)

	for i := 0; i < 5; i++ {
		err := cb.Execute(func() error {
			return nil
		})
		if err != nil {
			t.Fatalf("ejecución inesperadamente falló: %v", err)
		}
	}

	if cb.State() != StateClosed {
		t.Errorf("se esperaba StateClosed, obtenido: %v", cb.GetState())
	}
	if cb.Failures() != 0 {
		t.Errorf("se esperaba 0 fallos, obtenido: %d", cb.Failures())
	}
}

func TestCircuitBreaker_TripsToOpenAfterMaxFailures(t *testing.T) {
	maxFailures := 3
	cb := New("test-cb", maxFailures, 200*time.Millisecond)
	simulatedErr := errors.New("error simulado de conexion postgres")

	// 1. Provocar fallos hasta el límite
	for i := 1; i <= maxFailures; i++ {
		err := cb.Execute(func() error {
			return simulatedErr
		})
		if err != simulatedErr {
			t.Fatalf("intento %d: se esperaba simulatedErr, se obtuvo %v", i, err)
		}
	}

	// 2. Comprobar que el circuito ahora está OPEN
	if cb.State() != StateOpen {
		t.Fatalf("se esperaba StateOpen después de %d fallos, estado actual: %s", maxFailures, cb.GetState())
	}

	// 3. Verificar Fail Fast: el circuito abierto no debe ejecutar la función interna
	var executed atomic.Bool
	err := cb.Execute(func() error {
		executed.Store(true)
		return nil
	})

	if err != ErrCircuitOpen {
		t.Fatalf("se esperaba ErrCircuitOpen, se obtuvo: %v", err)
	}
	if executed.Load() {
		t.Fatal("la función interna fue ejecutada a pesar de que el circuito estaba OPEN (no hubo Fail Fast)")
	}
}

func TestCircuitBreaker_HalfOpenAndRecovery(t *testing.T) {
	timeout := 50 * time.Millisecond
	cb := New("test-recovery", 2, timeout)
	simulatedErr := errors.New("db caida")

	// Abrir circuito
	cb.Execute(func() error { return simulatedErr })
	cb.Execute(func() error { return simulatedErr })

	if cb.State() != StateOpen {
		t.Fatalf("se esperaba circuito OPEN")
	}

	// Esperar que transcurra el tiempo de enfriamiento (cooldown timeout)
	time.Sleep(timeout + 20*time.Millisecond)

	// La siguiente llamada debe entrar en Half-Open y tener éxito
	err := cb.Execute(func() error {
		return nil
	})
	if err != nil {
		t.Fatalf("llamada de prueba en Half-Open falló: %v", err)
	}

	// Debe haberse recuperado a CLOSED
	if cb.State() != StateClosed {
		t.Fatalf("se esperaba circuito recuperado a CLOSED, actual: %s", cb.GetState())
	}
	if cb.Failures() != 0 {
		t.Fatalf("se esperaba 0 fallos tras recuperación")
	}
}

func TestCircuitBreaker_ExecuteWithFallback(t *testing.T) {
	cb := New("test-fallback", 1, 100*time.Millisecond)
	cb.Trip() // Forzar circuito abierto

	var fallbackCalled bool
	err := cb.ExecuteWithFallback(
		func() error {
			return nil
		},
		func(origErr error) error {
			if origErr != ErrCircuitOpen {
				t.Errorf("fallback esperaba ErrCircuitOpen, obtuvo: %v", origErr)
			}
			fallbackCalled = true
			return nil // Recuperado por fallback
		},
	)

	if err != nil {
		t.Fatalf("fallback debió resolver el error, obtuvo: %v", err)
	}
	if !fallbackCalled {
		t.Fatal("el callback de fallback no fue invocado")
	}
}
