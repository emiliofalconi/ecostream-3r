-- ==============================================================================
-- EcoStream 3R - AquaGuardians: Script de Optimización SQL y Planes de Ejecución
-- Cátedra: Computación en la Nube (UCAB) - Semana 3
-- Objetivo: Optimizar consultas críticas (Leaderboard, Historial, Matchmaking)
-- ==============================================================================

-- 1. ÍNDICE COMPUESTO PARA LEADERBOARD (users)
-- Consulta optimizada:
--   SELECT id, username, total_eco_score, games_played, games_won, default_role
--   FROM users ORDER BY total_eco_score DESC, games_won DESC LIMIT 10;
-- Sin índice: Seq Scan en 'users' + Sort (O(N log N) en CPU y disco).
-- Con índice: Index Scan directo en B-Tree preordenado (O(log N + K)), tiempo < 1ms.
CREATE INDEX IF NOT EXISTS idx_users_leaderboard ON users(total_eco_score DESC, games_won DESC);

-- 2. ÍNDICE COMPUESTO PARA SALAS ACTIVAS (rooms)
-- Consulta optimizada:
--   SELECT id, room_code, room_name, status, max_players, simulation_endpoint, created_at
--   FROM rooms WHERE status IN (1, 2) ORDER BY created_at DESC LIMIT 20;
-- Evita Seq Scan al filtrar salas abiertas y ordenar por fecha de creación.
CREATE INDEX IF NOT EXISTS idx_rooms_status_created ON rooms(status, created_at DESC);

-- 3. ÍNDICES PARA ESTADÍSTICAS INDIVIDUALES (match_player_stats)
-- Optimiza consultas de perfil de jugador y agregaciones de litros ahorrados por usuario:
CREATE INDEX IF NOT EXISTS idx_match_player_stats_user_id ON match_player_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_match_player_stats_match_id ON match_player_stats(match_id);

-- 4. ÍNDICES PARA HISTORIAL DE PARTIDAS (matches)
-- Optimiza búsquedas directas por código de sala y filtrado por estado de victoria:
CREATE INDEX IF NOT EXISTS idx_matches_room_code ON matches(room_code);
CREATE INDEX IF NOT EXISTS idx_matches_victory_finished ON matches(is_victory, finished_at DESC);

-- 5. ÍNDICE EN MAPEO DE JUGADORES EN SALAS (room_players)
-- Permite validación instantánea O(1) de concurrencia de jugador en salas:
CREATE INDEX IF NOT EXISTS idx_room_players_user_id ON room_players(user_id);

-- ==============================================================================
-- VERIFICACIÓN CON EXPLAIN ANALYZE (Comentarios de referencia)
-- ==============================================================================
-- EXPLAIN ANALYZE
-- SELECT id, username, total_eco_score, games_played, games_won, default_role
-- FROM users
-- ORDER BY total_eco_score DESC, games_won DESC
-- LIMIT 10;
-- Resultado esperado con índice:
--   -> Limit  (cost=0.15..0.65 rows=10 width=84)
--        -> Index Scan using idx_users_leaderboard on users (cost=0.15..12.35 rows=240 width=84)
