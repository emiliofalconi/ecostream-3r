package resilience

import (
	"fmt"
	"time"

	"github.com/sony/gobreaker"
)

// CircuitBreakerManager gestiona circuit breakers nombrados
type CircuitBreakerManager struct {
	cb *gobreaker.CircuitBreaker
}

// NewCircuitBreaker crea un nuevo circuit breaker con umbrales configurables
func NewCircuitBreaker(name string) *CircuitBreakerManager {
	st := gobreaker.Settings{
		Name:        name,
		MaxRequests: 5,
		Interval:    10 * time.Second,
		Timeout:     5 * time.Second,
		ReadyToTrip: func(counts gobreaker.Counts) bool {
			failureRatio := float64(counts.TotalFailures) / float64(counts.Requests)
			return counts.Requests >= 5 && failureRatio >= 0.6
		},
		OnStateChange: func(name string, from gobreaker.State, to gobreaker.State) {
			fmt.Printf("[CIRCUIT-BREAKER] [%s] Estado cambió de %s a %s\n", name, from, to)
		},
	}

	return &CircuitBreakerManager{
		cb: gobreaker.NewCircuitBreaker(st),
	}
}

// Execute ejecuta una función protegida por el circuit breaker
func (c *CircuitBreakerManager) Execute(fn func() (interface{}, error)) (interface{}, error) {
	return c.cb.Execute(fn)
}

// State retorna el estado actual del breaker
func (c *CircuitBreakerManager) State() gobreaker.State {
	return c.cb.State()
}
