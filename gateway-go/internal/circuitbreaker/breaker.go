package circuitbreaker

import (
	"errors"
	"sync"
	"time"
)

type State int

const (
	StateClosed State = iota // Funcionando normal
	StateHalfOpen            // Probando recuperación
	StateOpen                // Disyuntor activado (rechaza peticiones)
)

var (
	ErrCircuitOpen = errors.New("circuit breaker abierto: servicio temporalmente no disponible")
)

type CircuitBreaker struct {
	mu           sync.Mutex
	name         string
	maxFailures  int
	timeout      time.Duration
	failures     int
	lastFailure  time.Time
	state        State
}

func New(name string, maxFailures int, timeout time.Duration) *CircuitBreaker {
	return &CircuitBreaker{
		name:        name,
		maxFailures: maxFailures,
		timeout:     timeout,
		state:       StateClosed,
	}
}

func (cb *CircuitBreaker) Execute(fn func() error) error {
	cb.mu.Lock()
	if cb.state == StateOpen {
		if time.Since(cb.lastFailure) > cb.timeout {
			cb.state = StateHalfOpen
		} else {
			cb.mu.Unlock()
			return ErrCircuitOpen
		}
	}
	cb.mu.Unlock()

	err := fn()

	cb.mu.Lock()
	defer cb.mu.Unlock()

	if err != nil {
		cb.failures++
		cb.lastFailure = time.Now()
		if cb.failures >= cb.maxFailures {
			cb.state = StateOpen
		}
		return err
	}

	// Éxito: restablecer circuito
	cb.failures = 0
	cb.state = StateClosed
	return nil
}

func (cb *CircuitBreaker) GetState() string {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	switch cb.state {
	case StateClosed:
		return "CLOSED (Healthy)"
	case StateHalfOpen:
		return "HALF-OPEN (Probing)"
	case StateOpen:
		return "OPEN (Tripped/Failed)"
	default:
		return "UNKNOWN"
	}
}
