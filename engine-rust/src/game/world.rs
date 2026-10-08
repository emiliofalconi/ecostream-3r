use std::collections::HashMap;

use super::entities::*;

pub const MAP_WIDTH: f32 = 800.0;
pub const MAP_HEIGHT: f32 = 600.0;
pub const INTERACTION_DISTANCE: f32 = 65.0;

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub struct GameWorld {
    pub room_id: String,
    pub tick: u64,
    pub remaining_seconds: u32,
    pub team_score: u32,
    pub difficulty: u32,
    pub players: HashMap<String, PlayerEntity>,
    pub pipes: Vec<PipeEntity>,
    pub valves: Vec<ValveEntity>,
    pub plants: Vec<TreatmentPlantEntity>,
    pub active_events: Vec<EventEntity>,
    pub metrics: WaterMetricsState,
    pub is_finished: bool,
    pub is_victory: bool,
    pub finish_reason: String,
}

impl GameWorld {
    pub fn new(room_id: String, difficulty: u32) -> Self {
        // Inicializar 4 tuberías distribuidas en el mapa
        let pipes = vec![
            PipeEntity {
                pipe_id: 1,
                x: 180.0,
                y: 150.0,
                is_leaking: true,
                leak_rate_liters_sec: 4.5,
                repair_progress_pct: 0.0,
                water_pressure_bar: 3.2,
            },
            PipeEntity {
                pipe_id: 2,
                x: 620.0,
                y: 180.0,
                is_leaking: false,
                leak_rate_liters_sec: 0.0,
                repair_progress_pct: 100.0,
                water_pressure_bar: 3.5,
            },
            PipeEntity {
                pipe_id: 3,
                x: 250.0,
                y: 420.0,
                is_leaking: true,
                leak_rate_liters_sec: 6.0,
                repair_progress_pct: 20.0,
                water_pressure_bar: 2.8,
            },
            PipeEntity {
                pipe_id: 4,
                x: 550.0,
                y: 450.0,
                is_leaking: false,
                leak_rate_liters_sec: 0.0,
                repair_progress_pct: 100.0,
                water_pressure_bar: 3.8,
            },
        ];

        // Inicializar 2 válvulas de desvío
        let valves = vec![
            ValveEntity {
                valve_id: 1,
                x: 350.0,
                y: 200.0,
                destination: 1, // 1 = Sewer (derroche inicial)
                flow_rate_liters_sec: 8.0,
            },
            ValveEntity {
                valve_id: 2,
                x: 480.0,
                y: 380.0,
                destination: 2, // 2 = Irrigation (reuso agrícola)
                flow_rate_liters_sec: 10.0,
            },
        ];

        // Planta de tratamiento de aguas residuales
        let plants = vec![TreatmentPlantEntity {
            plant_id: 1,
            x: 400.0,
            y: 520.0,
            filter_health_pct: 80.0,
            sludge_level_pct: 15.0,
            purification_rate_lps: 12.0,
            is_operating: true,
        }];

        Self {
            room_id,
            tick: 0,
            remaining_seconds: 300, // 5 minutos de partida cooperativa
            team_score: 0,
            difficulty: if difficulty == 0 { 1 } else { difficulty },
            players: HashMap::new(),
            pipes,
            valves,
            plants,
            active_events: Vec::new(),
            metrics: WaterMetricsState::default(),
            is_finished: false,
            is_victory: false,
            finish_reason: String::new(),
        }
    }

    pub fn add_or_update_player(&mut self, player_id: String, username: String, role: i32) {
        if let Some(existing) = self.players.get_mut(&player_id) {
            existing.is_connected = true;
            existing.disconnected_at = None;
        } else {
            self.players.insert(
                player_id.clone(),
                PlayerEntity::new(player_id, username, role),
            );
        }
    }

    pub fn mark_player_disconnected(&mut self, player_id: &str) {
        if let Some(player) = self.players.get_mut(player_id) {
            player.is_connected = false;
            player.disconnected_at = Some(std::time::Instant::now());
        }
    }

    pub fn apply_move(&mut self, player_id: &str, dir_x: f32, dir_y: f32, dt: f32) {
        if let Some(player) = self.players.get_mut(player_id) {
            // Normalización y validación estricta de vector de dirección (Anti-Speedhack)
            let mut dx = dir_x;
            let mut dy = dir_y;
            let length = (dx * dx + dy * dy).sqrt();

            if length > 1.0 {
                dx /= length;
                dy /= length;
            }

            let new_x = player.x + dx * player.speed * dt;
            let new_y = player.y + dy * player.speed * dt;

            // Bounding box del escenario
            player.x = new_x.clamp(20.0, MAP_WIDTH - 20.0);
            player.y = new_y.clamp(20.0, MAP_HEIGHT - 20.0);
            player.vx = dx * player.speed;
            player.vy = dy * player.speed;
        }
    }

    pub fn apply_repair_pipe(&mut self, player_id: &str, pipe_id: u32, dt: f32) -> bool {
        let (player_x, player_y, player_role) = match self.players.get(player_id) {
            Some(p) => (p.x, p.y, p.role),
            None => return false,
        };

        if let Some(pipe) = self.pipes.iter_mut().find(|p| p.pipe_id == pipe_id) {
            let dist = ((pipe.x - player_x).powi(2) + (pipe.y - player_y).powi(2)).sqrt();
            if dist > INTERACTION_DISTANCE {
                return false; // Jugador demasiado lejos de la tubería
            }

            if !pipe.is_leaking {
                return false;
            }

            // Bono de reparación para el Rol Plumber (1)
            let repair_mult = if player_role == 1 { 1.5 } else { 1.0 };
            pipe.repair_progress_pct += 25.0 * repair_mult * dt;

            if pipe.repair_progress_pct >= 100.0 {
                pipe.repair_progress_pct = 100.0;
                pipe.is_leaking = false;
                pipe.leak_rate_liters_sec = 0.0;

                // Premiar al jugador y al equipo
                if let Some(player) = self.players.get_mut(player_id) {
                    player.repairs_done += 1;
                    player.water_saved_liters += 150.0;
                    player.current_score += 200;
                }
                self.metrics.total_liters_saved += 150.0;
                self.team_score += 250;
            }
            return true;
        }
        false
    }

    pub fn apply_divert_valve(&mut self, player_id: &str, valve_id: u32, destination: i32) -> bool {
        let (player_x, player_y, player_role) = match self.players.get(player_id) {
            Some(p) => (p.x, p.y, p.role),
            None => return false,
        };

        if let Some(valve) = self.valves.iter_mut().find(|v| v.valve_id == valve_id) {
            let dist = ((valve.x - player_x).powi(2) + (valve.y - player_y).powi(2)).sqrt();
            if dist > INTERACTION_DISTANCE {
                return false;
            }

            valve.destination = destination;

            if destination == 2 {
                // Desvío a Riego Comunitario (Reuso): suma puntos
                let bonus = if player_role == 2 { 100 } else { 50 };
                if let Some(player) = self.players.get_mut(player_id) {
                    player.current_score += bonus;
                }
                self.team_score += bonus;
            }
            return true;
        }
        false
    }

    pub fn apply_recycle_op(&mut self, player_id: &str, plant_id: u32, operation: i32) -> bool {
        let (player_x, player_y, player_role) = match self.players.get(player_id) {
            Some(p) => (p.x, p.y, p.role),
            None => return false,
        };

        if let Some(plant) = self.plants.iter_mut().find(|pl| pl.plant_id == plant_id) {
            let dist = ((plant.x - player_x).powi(2) + (plant.y - player_y).powi(2)).sqrt();
            if dist > INTERACTION_DISTANCE + 20.0 {
                return false;
            }

            let bonus = if player_role == 3 { 80 } else { 40 };

            match operation {
                0 => {
                    // Recargar filtro
                    plant.filter_health_pct = 100.0;
                }
                1 => {
                    // Purgar lodos
                    plant.sludge_level_pct = 0.0;
                }
                2 => {
                    // Alternar bomba
                    plant.is_operating = !plant.is_operating;
                }
                _ => return false,
            }

            if let Some(player) = self.players.get_mut(player_id) {
                player.current_score += bonus;
            }
            self.team_score += bonus;
            return true;
        }
        false
    }

    pub fn update(&mut self, dt: f32) {
        if self.is_finished {
            return;
        }

        self.tick += 1;

        // Actualizar reloj por segundo (cada 20 ticks = 1s a 20Hz)
        if self.tick % 20 == 0 && self.remaining_seconds > 0 {
            self.remaining_seconds -= 1;
        }

        // 1. MECÁNICA REDUCIR: Fugas activas reducen el nivel del embalse
        let mut total_leak_lps = 0.0;
        for pipe in &self.pipes {
            if pipe.is_leaking {
                total_leak_lps += pipe.leak_rate_liters_sec;
            }
        }
        // Desgaste hídrico: factor de dificultad
        let leak_drain_pct = (total_leak_lps * 0.015 * self.difficulty as f32) * dt;
        self.metrics.reservoir_level_pct = (self.metrics.reservoir_level_pct - leak_drain_pct).max(0.0);

        // 2. MECÁNICA REUSAR: Flujo hacia riego acumula litros reusados
        for valve in &self.valves {
            if valve.destination == 2 {
                // Riego (Reuso)
                let reused = valve.flow_rate_liters_sec * dt;
                self.metrics.total_liters_reused += reused;
                self.team_score += (reused * 0.1) as u32;
            } else if valve.destination == 1 {
                // Sewer (Derroche innecesario)
                let wasted = valve.flow_rate_liters_sec * 0.005 * dt;
                self.metrics.reservoir_level_pct = (self.metrics.reservoir_level_pct - wasted).max(0.0);
            }
        }

        // 3. MECÁNICA RECICLAR: Planta procesa aguas residuales si está operativa
        for plant in &mut self.plants {
            if plant.is_operating && plant.filter_health_pct > 10.0 && plant.sludge_level_pct < 95.0 {
                let recycled = plant.purification_rate_lps * dt;
                self.metrics.total_liters_recycled += recycled;
                self.metrics.water_purity_pct = (self.metrics.water_purity_pct + 0.05 * dt).min(100.0);

                // Desgaste progresivo del filtro y acumulación de sedimentos
                plant.filter_health_pct = (plant.filter_health_pct - 0.2 * dt).max(0.0);
                plant.sludge_level_pct = (plant.sludge_level_pct + 0.3 * dt).min(100.0);
            } else {
                // Si la planta no opera o está atascada, la pureza se degrada
                self.metrics.water_purity_pct = (self.metrics.water_purity_pct - 0.03 * dt).max(20.0);
            }
        }

        // Condición de Victoria / Derrota
        if self.metrics.reservoir_level_pct <= 0.0 {
            self.is_finished = true;
            self.is_victory = false;
            self.finish_reason = "Sequía crítica: El embalse comunal se ha secado".to_string();
        } else if self.remaining_seconds == 0 {
            self.is_finished = true;
            self.is_victory = self.metrics.reservoir_level_pct >= 25.0;
            self.finish_reason = if self.is_victory {
                "¡Victoria ecológica! La cuadrilla preservó el suministro hídrico".to_string()
            } else {
                "Suministro insuficiente: El embalse finalizó por debajo del 25%".to_string()
            };
        }
    }
}
