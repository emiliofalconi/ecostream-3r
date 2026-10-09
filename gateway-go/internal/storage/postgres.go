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

// AutoMigrate asegura que las tablas del esquema existan e inicializa datos de semilla de forma idempotente
func (p *PostgresDB) AutoMigrate(ctx context.Context) error {
	var exists bool
	checkQuery := `SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users');`
	if err := p.DB.QueryRowContext(ctx, checkQuery).Scan(&exists); err != nil {
		return fmt.Errorf("error al consultar existencia de tablas: %w", err)
	}

	if !exists {
		log.Println("[INFO] [DB] Base de datos vacía detectada. Aplicando esquema DDL y semillas iniciales...")
		_, err := p.DB.ExecContext(ctx, ddlAutoMigrateSchema)
		if err != nil {
			return fmt.Errorf("error al ejecutar DDL automático: %w", err)
		}
		log.Println("[INFO] [DB] Esquema relacional DDL aplicado con éxito.")
	} else {
		log.Println("[INFO] [DB] Esquema relacional verificado (tablas activas).")
	}
	return nil
}

const ddlAutoMigrateSchema = `
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY DEFAULT ('usr_' || substr(md5(random()::text || clock_timestamp()::text), 1, 16)),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    default_role INT NOT NULL DEFAULT 4,
    games_played INT NOT NULL DEFAULT 0,
    games_won INT NOT NULL DEFAULT 0,
    total_eco_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rooms (
    id VARCHAR(64) PRIMARY KEY DEFAULT ('rm_' || substr(md5(random()::text || clock_timestamp()::text), 1, 16)),
    room_code VARCHAR(10) UNIQUE NOT NULL,
    room_name VARCHAR(100) NOT NULL,
    host_user_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    status INT NOT NULL DEFAULT 1,
    current_players INT NOT NULL DEFAULT 1,
    max_players INT NOT NULL DEFAULT 4,
    difficulty_level INT NOT NULL DEFAULT 1,
    simulation_endpoint VARCHAR(255) NOT NULL DEFAULT 'localhost:50052',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_players_limit CHECK (current_players >= 0 AND current_players <= max_players)
);

CREATE TABLE IF NOT EXISTS room_players (
    id BIGSERIAL PRIMARY KEY,
    room_id VARCHAR(64) NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    selected_role INT NOT NULL DEFAULT 4,
    is_host BOOLEAN NOT NULL DEFAULT FALSE,
    is_ready BOOLEAN NOT NULL DEFAULT FALSE,
    is_bot BOOLEAN NOT NULL DEFAULT FALSE,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_room_user UNIQUE (room_id, user_id)
);

CREATE TABLE IF NOT EXISTS matches (
    id VARCHAR(64) PRIMARY KEY DEFAULT ('mtc_' || substr(md5(random()::text || clock_timestamp()::text), 1, 16)),
    room_id VARCHAR(64),
    room_code VARCHAR(10),
    is_victory BOOLEAN NOT NULL,
    end_reason VARCHAR(255) NOT NULL,
    final_score INT NOT NULL DEFAULT 0,
    final_reservoir_pct DOUBLE PRECISION NOT NULL,
    final_water_purity_pct DOUBLE PRECISION NOT NULL,
    total_liters_saved DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    total_liters_reused DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    total_liters_recycled DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    duration_seconds INT NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS match_player_stats (
    id BIGSERIAL PRIMARY KEY,
    match_id VARCHAR(64) NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    user_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(50) NOT NULL,
    role_played INT NOT NULL,
    repairs_done INT NOT NULL DEFAULT 0,
    water_saved_liters DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    water_recycled_liters DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    individual_points INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    service_name VARCHAR(50) NOT NULL DEFAULT 'gateway-go',
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'INFO',
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_rooms_room_code ON rooms(room_code);
CREATE INDEX IF NOT EXISTS idx_rooms_status ON rooms(status);
CREATE INDEX IF NOT EXISTS idx_room_players_room_id ON room_players(room_id);
CREATE INDEX IF NOT EXISTS idx_matches_finished_at ON matches(finished_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);

INSERT INTO users (id, username, email, password_hash, default_role, games_played, games_won, total_eco_score)
VALUES 
    ('usr_admin_eco', 'admin_eco', 'admin@ecostream.ucab.ve', '$2b$10$vbMpDUhsSD8AJjD4Ci8xs.GVuut3Mtka8khNCLGvRRKmuHDKiNjg6', 4, 10, 8, 4500.0),
    ('usr_victor_admin', 'VictorAdmin', 'victor@ecostream.ucab.ve', '$2b$10$vbMpDUhsSD8AJjD4Ci8xs.GVuut3Mtka8khNCLGvRRKmuHDKiNjg6', 2, 10, 8, 4500.0),
    ('usr_plumber_hero', 'PlumberHero', 'plumber@ecostream.ucab.ve', '$2b$10$vbMpDUhsSD8AJjD4Ci8xs.GVuut3Mtka8khNCLGvRRKmuHDKiNjg6', 1, 5, 4, 2100.0),
    ('usr_eco_bot_01', 'EcoBot01', 'bot01@ecostream.local', '$2b$10$vbMpDUhsSD8AJjD4Ci8xs.GVuut3Mtka8khNCLGvRRKmuHDKiNjg6', 4, 20, 15, 8900.0)
ON CONFLICT (username) DO NOTHING;
`
