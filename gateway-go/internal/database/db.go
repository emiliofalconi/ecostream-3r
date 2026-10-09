package database

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"time"

	"github.com/Makmadon/ecostream-3r/gateway-go/internal/circuitbreaker"
	_ "github.com/lib/pq"
)

type DB struct {
	*sql.DB
	Breaker *circuitbreaker.CircuitBreaker
}

func Connect(dbURL string) (*DB, error) {
	db, err := sql.Open("postgres", dbURL)
	if err != nil {
		return nil, fmt.Errorf("error al abrir conexión con PostgreSQL: %w", err)
	}

	// Configuración de Connection Pooling
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(10)
	db.SetConnMaxLifetime(5 * time.Minute)
	db.SetConnMaxIdleTime(2 * time.Minute)

	// Intento de conexión inicial con reintentos
	var pingErr error
	for i := 1; i <= 5; i++ {
		pingErr = db.Ping()
		if pingErr == nil {
			log.Println("[DATABASE] Conexión establecida exitosamente con PostgreSQL 16")
			return &DB{DB: db}, nil
		}
		log.Printf("[DATABASE] Esperando base de datos (intento %d/5): %v", i, pingErr)
		time.Sleep(2 * time.Second)
	}

	return &DB{DB: db}, fmt.Errorf("no se pudo conectar a la base de datos tras 5 intentos: %w", pingErr)
}

func (d *DB) WithBreaker(breaker *circuitbreaker.CircuitBreaker) *DB {
	d.Breaker = breaker
	return d
}

func (d *DB) PingCheck() bool {
	if d == nil || d.DB == nil {
		return false
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	if d.Breaker != nil {
		var pingErr error
		err := d.Breaker.Execute(func() error {
			pingErr = d.DB.PingContext(ctx)
			return pingErr
		})
		return err == nil && pingErr == nil
	}

	return d.DB.PingContext(ctx) == nil
}
