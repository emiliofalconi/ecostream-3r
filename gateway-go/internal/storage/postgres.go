package storage

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"time"

	_ "github.com/lib/pq"
)

// PostgresDB envuelve la conexión a PostgreSQL con configuraciones de pooling
type PostgresDB struct {
	DB *sql.DB
}

// NewPostgresDB inicializa el pool de conexiones a PostgreSQL
func NewPostgresDB(databaseURL string) (*PostgresDB, error) {
	db, err := sql.Open("postgres", databaseURL)
	if err != nil {
		return nil, fmt.Errorf("error al abrir conexión PostgreSQL: %w", err)
	}

	// Parámetros de pooling optimizados para concurrencia escolar/producción
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(10)
	db.SetConnMaxLifetime(5 * time.Minute)
	db.SetConnMaxIdleTime(2 * time.Minute)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := db.PingContext(ctx); err != nil {
		log.Printf("[WARN] No se pudo verificar Ping inmediato a PostgreSQL: %v (se reintentará en queries)", err)
	} else {
		log.Println("[INFO] Conexión establecida exitosamente con PostgreSQL 16")
	}

	return &PostgresDB{DB: db}, nil
}

// Ping verifica la salud de la conexión a PostgreSQL
func (p *PostgresDB) Ping(ctx context.Context) error {
	return p.DB.PingContext(ctx)
}

// Close cierra el pool de conexiones
func (p *PostgresDB) Close() error {
	return p.DB.Close()
}
