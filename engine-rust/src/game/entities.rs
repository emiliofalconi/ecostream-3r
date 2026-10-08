use std::time::Instant;

#[derive(Debug, Clone)]
pub struct PlayerEntity {
    pub player_id: String,
    pub username: String,
    pub role: i32,
    pub x: f32,
    pub y: f32,
    pub vx: f32,
    pub vy: f32,
    pub speed: f32,
    pub is_connected: bool,
    pub disconnected_at: Option<Instant>,
    pub carrying_item: String,
    pub current_score: u32,
    pub repairs_done: u32,
    pub water_saved_liters: f32,
    pub water_recycled_liters: f32,
}

impl PlayerEntity {
    pub fn new(player_id: String, username: String, role: i32) -> Self {
        // Rol 1: Plumber (más veloz y mayor reparación), Rol 2: Hydraulic, Rol 3: Chemical, Rol 4: Generalist
        let speed = if role == 1 { 140.0 } else { 120.0 };

        Self {
            player_id,
            username,
            role,
            x: 400.0,
            y: 300.0,
            vx: 0.0,
            vy: 0.0,
            speed,
            is_connected: true,
            disconnected_at: None,
            carrying_item: String::new(),
            current_score: 0,
            repairs_done: 0,
            water_saved_liters: 0.0,
            water_recycled_liters: 0.0,
        }
    }
}

#[derive(Debug, Clone)]
pub struct PipeEntity {
    pub pipe_id: u32,
    pub x: f32,
    pub y: f32,
    pub is_leaking: bool,
    pub leak_rate_liters_sec: f32,
    pub repair_progress_pct: f32,
    pub water_pressure_bar: f32,
}

#[derive(Debug, Clone)]
pub struct ValveEntity {
    pub valve_id: u32,
    pub x: f32,
    pub y: f32,
    pub destination: i32, // 1: sewer, 2: irrigation, 3: plant
    pub flow_rate_liters_sec: f32,
}

#[derive(Debug, Clone)]
pub struct TreatmentPlantEntity {
    pub plant_id: u32,
    pub x: f32,
    pub y: f32,
    pub filter_health_pct: f32,
    pub sludge_level_pct: f32,
    pub purification_rate_lps: f32,
    pub is_operating: bool,
}

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub struct EventEntity {
    pub event_id: u32,
    pub event_type: i32,
    pub title: String,
    pub description: String,
    pub remaining_seconds: u32,
    pub severity_multiplier: f32,
}

#[derive(Debug, Clone)]
pub struct WaterMetricsState {
    pub reservoir_level_pct: f32,
    pub water_purity_pct: f32,
    pub total_liters_saved: f32,
    pub total_liters_reused: f32,
    pub total_liters_recycled: f32,
}

impl Default for WaterMetricsState {
    fn default() -> Self {
        Self {
            reservoir_level_pct: 100.0,
            water_purity_pct: 85.0,
            total_liters_saved: 0.0,
            total_liters_reused: 0.0,
            total_liters_recycled: 0.0,
        }
    }
}
