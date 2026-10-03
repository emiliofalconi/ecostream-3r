use std::collections::HashMap;
use std::time::Instant;
use crate::proto::ecostream::v1::*;

/// Estructura de Simulación Autoritativa de una Sala (20 Ticks/segundo)
pub struct GameRoomSimulation {
    pub room_id: String,
    pub tick: u64,
    pub start_time: Instant,
    pub match_duration_seconds: u32,
    pub remaining_seconds: u32,
    pub team_score: u32,
    
    // Métricas ecológicas 3R
    pub reservoir_level_pct: f32,
    pub water_purity_pct: f32,
    pub total_liters_saved: f32,
    pub total_liters_reused: f32,
    pub total_liters_recycled: f32,

    // Entidades del mundo
    pub players: HashMap<String, PlayerEntityState>,
    pub pipes: Vec<PipeEntityState>,
    pub valves: Vec<ValveEntityState>,
    pub plants: Vec<TreatmentPlantEntityState>,
    pub active_events: Vec<ActiveEvent>,

    // Resiliencia: Mapa de tickets de sesión para reconexión (< 5s) (agregado por Victor)
    pub session_tickets: HashMap<String, String>, // player_id -> reconnect_ticket
    pub last_snapshot: Option<GameWorldState>,
}

impl GameRoomSimulation {
    pub fn new(room_id: String) -> Self {
        // Tuberías iniciales del mapa Top-Down
        let initial_pipes = vec![
            PipeEntityState {
                pipe_id: 1,
                position: Some(Vector2D { x: 10.0, y: 15.0 }),
                is_leaking: false,
                leak_rate_liters_sec: 0.0,
                repair_progress_pct: 100.0,
                water_pressure_bar: 3.5,
            },
            PipeEntityState {
                pipe_id: 2,
                position: Some(Vector2D { x: 25.0, y: 30.0 }),
                is_leaking: true, // Fuga activa inicial
                leak_rate_liters_sec: 8.5,
                repair_progress_pct: 0.0,
                water_pressure_bar: 4.2,
            },
            PipeEntityState {
                pipe_id: 3,
                position: Some(Vector2D { x: 40.0, y: 18.0 }),
                is_leaking: false,
                leak_rate_liters_sec: 0.0,
                repair_progress_pct: 100.0,
                water_pressure_bar: 3.8,
            },
        ];

        // Válvulas de desvío de aguas grises (2. REUSAR)
        let initial_valves = vec![
            ValveEntityState {
                valve_id: 1,
                position: Some(Vector2D { x: 18.0, y: 22.0 }),
                current_destination: WaterDestination::DestinationIrrigation as i32,
                flow_rate_liters_sec: 12.0,
            },
            ValveEntityState {
                valve_id: 2,
                position: Some(Vector2D { x: 35.0, y: 40.0 }),
                current_destination: WaterDestination::DestinationSewer as i32,
                flow_rate_liters_sec: 5.0,
            },
        ];

        // Planta de filtrado ecológico (3. RECICLAR)
        let initial_plants = vec![
            TreatmentPlantEntityState {
                plant_id: 1,
                position: Some(Vector2D { x: 50.0, y: 50.0 }),
                filter_health_pct: 95.0,
                sludge_level_pct: 15.0,
                purification_rate_lps: 15.0,
                is_operating: true,
            },
        ];

        Self {
            room_id,
            tick: 0,
            start_time: Instant::now(),
            match_duration_seconds: 180,
            remaining_seconds: 180,
            team_score: 0,
            reservoir_level_pct: 100.0,
            water_purity_pct: 96.0,
            total_liters_saved: 0.0,
            total_liters_reused: 0.0,
            total_liters_recycled: 0.0,
            players: HashMap::new(),
            pipes: initial_pipes,
            valves: initial_valves,
            plants: initial_plants,
            active_events: Vec::new(),
            session_tickets: HashMap::new(),
            last_snapshot: None,
        }
    }

    /// Registrar o actualizar jugador en la sala
    pub fn upsert_player(&mut self, player_id: String, username: String, role: i32) -> String {
        let ticket = format!("tkt_reconn_{}_{}", player_id, self.tick);
        self.session_tickets.insert(player_id.clone(), ticket.clone());

        self.players.entry(player_id.clone()).or_insert_with(|| PlayerEntityState {
            player_id,
            username,
            role,
            position: Some(Vector2D { x: 20.0, y: 20.0 }),
            velocity: Some(Vector2D { x: 0.0, y: 0.0 }),
            is_interacting: false,
            current_score: 0,
            is_connected: true,
            carrying_item: "wrench".to_string(),
        });

        ticket
    }

    /// Aplicar acción despachada por el cliente
    pub fn apply_action(&mut self, player_id: &str, action: PlayerAction) {
        if let Some(action_type) = action.action_type {
            match action_type {
                // 1. REDUCIR: Reparación de fugas a presión
                player_action::ActionType::RepairPipe(repair) => {
                    if let Some(pipe) = self.pipes.iter_mut().find(|p| p.pipe_id == repair.pipe_id) {
                        pipe.repair_progress_pct = (pipe.repair_progress_pct + repair.repair_progress_delta).min(100.0);
                        if pipe.repair_progress_pct >= 100.0 && pipe.is_leaking {
                            pipe.is_leaking = false;
                            pipe.leak_rate_liters_sec = 0.0;
                            self.total_liters_saved += 75.0;
                            self.team_score += 150;
                            if let Some(p) = self.players.get_mut(player_id) {
                                p.current_score += 150;
                            }
                        }
                    }
                }
                // 2. REUSAR: Desvío de compuertas hacia huertos
                player_action::ActionType::DivertValve(divert) => {
                    if let Some(valve) = self.valves.iter_mut().find(|v| v.valve_id == divert.valve_id) {
                        valve.current_destination = divert.destination;
                        if divert.destination == WaterDestination::DestinationIrrigation as i32 {
                            self.total_liters_reused += 20.0;
                            self.team_score += 50;
                        }
                    }
                }
                // 3. RECICLAR: Planta biológica de filtración
                player_action::ActionType::OperateRecycle(recycle) => {
                    if let Some(plant) = self.plants.iter_mut().find(|pl| pl.plant_id == recycle.plant_id) {
                        plant.filter_health_pct = 100.0;
                        plant.sludge_level_pct = (plant.sludge_level_pct - 30.0).max(0.0);
                        self.total_liters_recycled += 50.0;
                        self.water_purity_pct = (self.water_purity_pct + 2.0).min(100.0);
                        self.team_score += 100;
                    }
                }
                // Movimiento del avatar
                player_action::ActionType::Move(mv) => {
                    if let Some(p) = self.players.get_mut(player_id) {
                        p.position = mv.target_position;
                        p.velocity = mv.velocity;
                    }
                }
                _ => {}
            }
        }
    }

    /// Actualización del Bucle Autoritativo (Llamado cada 50ms = 20 Ticks/seg)
    pub fn update_tick(&mut self) -> GameWorldState {
        self.tick += 1;

        // Drenaje continuo del embalse según fugas y demanda
        let mut total_leak_rate = 0.0;
        for pipe in &self.pipes {
            if pipe.is_leaking {
                total_leak_rate += pipe.leak_rate_liters_sec;
            }
        }

        let drainage_per_tick = 0.005 + (total_leak_rate * 0.001);
        self.reservoir_level_pct = (self.reservoir_level_pct - drainage_per_tick).max(0.0);

        // Generar fuga aleatoria cada 200 ticks (~10 seg) si no hay demasiadas
        if self.tick % 200 == 0 {
            if let Some(pipe) = self.pipes.iter_mut().find(|p| !p.is_leaking) {
                pipe.is_leaking = true;
                pipe.leak_rate_liters_sec = 6.0;
                pipe.repair_progress_pct = 0.0;
            }
        }

        // Construir métricas
        let metrics = WaterMetrics {
            reservoir_level_pct: (self.reservoir_level_pct * 100.0).round() / 100.0,
            water_purity_pct: (self.water_purity_pct * 100.0).round() / 100.0,
            total_liters_saved: self.total_liters_saved,
            total_liters_reused: self.total_liters_reused,
            total_liters_recycled: self.total_liters_recycled,
        };

        let elapsed = self.start_time.elapsed().as_secs() as u32;
        self.remaining_seconds = self.match_duration_seconds.saturating_sub(elapsed);

        let state = GameWorldState {
            tick: self.tick,
            water_metrics: Some(metrics),
            team_score: self.team_score,
            remaining_seconds: self.remaining_seconds,
            players: self.players.values().cloned().collect(),
            pipes: self.pipes.clone(),
            valves: self.valves.clone(),
            plants: self.plants.clone(),
            active_events: self.active_events.clone(),
        };

        self.last_snapshot = Some(state.clone());
        state
    }
}
