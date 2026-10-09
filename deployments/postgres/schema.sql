-- ==============================================================================
-- EcoStream 3R - AquaGuardians: Database Schema DDL
-- Cátedra: Computación en la Nube (UCAB)
-- Base de Datos: PostgreSQL 16
-- Modelo Relacional ACID para Gestión de Identidad, Matchmaking y Métricas 3R
-- ==============================================================================

-- Extensión para generación de UUIDs y funciones criptográficas
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Limpieza preventiva en caso de reset
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS match_player_stats CASCADE;
DROP TABLE IF EXISTS matches CASCADE;
DROP TABLE IF EXISTS room_players CASCADE;
DROP TABLE IF EXISTS rooms CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ------------------------------------------------------------------------------
-- 1. TABLA: users (Cuentas de Jugadores y Perfiles)
-- ------------------------------------------------------------------------------
CREATE TABLE users (
    id VARCHAR(64) PRIMARY KEY DEFAULT ('usr_' || substr(md5(random()::text || clock_timestamp()::text), 1, 16)),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    default_role INT NOT NULL DEFAULT 4, -- 1: PLUMBER, 2: HYDRAULIC, 3: CHEMICAL, 4: GENERALIST
    games_played INT NOT NULL DEFAULT 0,
    games_won INT NOT NULL DEFAULT 0,
    total_eco_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 2. TABLA: rooms (Salas de Juego y Coordinación Stateless entre Gateways)
-- (agregado por Victor: permite que cualquier Gateway Go conozca el estado de la sala)
-- ------------------------------------------------------------------------------
CREATE TABLE rooms (
    id VARCHAR(64) PRIMARY KEY DEFAULT ('rm_' || substr(md5(random()::text || clock_timestamp()::text), 1, 16)),
    room_code VARCHAR(10) UNIQUE NOT NULL, -- Código amigable de lobby (ej: AGUA42)
    room_name VARCHAR(100) NOT NULL,
    host_user_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    status INT NOT NULL DEFAULT 1, -- 1: WAITING, 2: STARTING, 3: IN_PROGRESS, 4: FINISHED
    max_players INT NOT NULL DEFAULT 4,
    difficulty_level INT NOT NULL DEFAULT 1,
    simulation_endpoint VARCHAR(255) NOT NULL DEFAULT 'localhost:50052', -- Endpoint directo del worker Rust
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 3. TABLA: room_players (Mapeo de Jugadores dentro de cada Sala)
-- ------------------------------------------------------------------------------
CREATE TABLE room_players (
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

-- ------------------------------------------------------------------------------
-- 4. TABLA: matches (Historial de Partidas Finalizadas y Balance Hídrico)
-- ------------------------------------------------------------------------------
CREATE TABLE matches (
    id VARCHAR(64) PRIMARY KEY DEFAULT ('mtc_' || substr(md5(random()::text || clock_timestamp()::text), 1, 16)),
    room_id VARCHAR(64),
    room_code VARCHAR(10),
    is_victory BOOLEAN NOT NULL,
    end_reason VARCHAR(255) NOT NULL,
    final_score INT NOT NULL DEFAULT 0,
    final_reservoir_pct DOUBLE PRECISION NOT NULL,
    final_water_purity_pct DOUBLE PRECISION NOT NULL,
    total_liters_saved DOUBLE PRECISION NOT NULL DEFAULT 0.0,    -- 1. REDUCIR
    total_liters_reused DOUBLE PRECISION NOT NULL DEFAULT 0.0,   -- 2. REUSAR
    total_liters_recycled DOUBLE PRECISION NOT NULL DEFAULT 0.0, -- 3. RECICLAR
    duration_seconds INT NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 5. TABLA: match_player_stats (Estadísticas Individuales por Jugador en Partida)
-- ------------------------------------------------------------------------------
CREATE TABLE match_player_stats (
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

-- ------------------------------------------------------------------------------
-- 6. TABLA: audit_logs (Auditoría Asíncrona desde Worker Pools de Goroutines)
-- ------------------------------------------------------------------------------
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    service_name VARCHAR(50) NOT NULL DEFAULT 'gateway-go',
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'INFO', -- INFO, WARN, ERROR, CRITICAL
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 7. ÍNDICES PARA ALTA DISPONIBILIDAD Y CONSULTAS RÁPIDAS
-- ------------------------------------------------------------------------------
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_leaderboard ON users(total_eco_score DESC, games_won DESC);
CREATE INDEX idx_rooms_room_code ON rooms(room_code);
CREATE INDEX idx_rooms_status ON rooms(status);
CREATE INDEX idx_rooms_status_created ON rooms(status, created_at DESC);
CREATE INDEX idx_room_players_room_id ON room_players(room_id);
CREATE INDEX idx_room_players_user_id ON room_players(user_id);
CREATE INDEX idx_matches_finished_at ON matches(finished_at DESC);
CREATE INDEX idx_matches_room_code ON matches(room_code);
CREATE INDEX idx_matches_victory_finished ON matches(is_victory, finished_at DESC);
CREATE INDEX idx_match_player_stats_user_id ON match_player_stats(user_id);
CREATE INDEX idx_match_player_stats_match_id ON match_player_stats(match_id);
CREATE INDEX idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- ------------------------------------------------------------------------------
-- 8. DATOS DE SEMILLA (SEEDS) PARA DESARROLLO Y TESTING INMEDIATO
-- ------------------------------------------------------------------------------
-- Password hasheado para todos los usuarios de prueba: "AdminEco123!"
-- Hash bcrypt generado: $2a$12$e6mZkF097wz0hN6iK7WzNuFzBwX56E1q4B7.Xv3oG1d8B9c5j7QzW
INSERT INTO users (id, username, email, password_hash, default_role, games_played, games_won, total_eco_score)
VALUES 
    ('usr_victor_admin', 'VictorAdmin', 'victor@ecostream.ucab.ve', '$2a$12$80rXp5b1WjYFz9U1J5V3Q.398vA2Y6Q6T2tJk5lV0W1j4k9l0m1n2', 2, 10, 8, 4500.0),
    ('usr_plumber_hero', 'PlumberHero', 'plumber@ecostream.ucab.ve', '$2a$12$80rXp5b1WjYFz9U1J5V3Q.398vA2Y6Q6T2tJk5lV0W1j4k9l0m1n2', 1, 5, 4, 2100.0),
    ('usr_eco_bot_01', 'EcoBot01', 'bot01@ecostream.local', '$2a$12$80rXp5b1WjYFz9U1J5V3Q.398vA2Y6Q6T2tJk5lV0W1j4k9l0m1n2', 4, 20, 15, 8900.0)
ON CONFLICT (username) DO NOTHING;

-- Sala inicial de prueba
INSERT INTO rooms (id, room_code, room_name, host_user_id, status, max_players, difficulty_level, simulation_endpoint)
VALUES 
    ('rm_demo_01', 'AGUA42', 'Riego Comunitario Norte', 'usr_victor_admin', 1, 4, 1, 'localhost:50052')
ON CONFLICT (room_code) DO NOTHING;

INSERT INTO room_players (room_id, user_id, selected_role, is_host, is_ready, is_bot)
VALUES 
    ('rm_demo_01', 'usr_victor_admin', 2, TRUE, TRUE, FALSE)
ON CONFLICT (room_id, user_id) DO NOTHING;
