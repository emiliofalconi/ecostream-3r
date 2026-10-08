use crate::game::world::GameWorld;
use crate::proto::ecostream::v1::*;

pub fn world_to_proto_state(world: &GameWorld) -> GameWorldState {
    let players = world
        .players
        .values()
        .map(|p| PlayerEntityState {
            player_id: p.player_id.clone(),
            username: p.username.clone(),
            role: p.role,
            position: Some(Vector2D { x: p.x, y: p.y }),
            velocity: Some(Vector2D { x: p.vx, y: p.vy }),
            is_interacting: false,
            current_score: p.current_score,
            is_connected: p.is_connected,
            carrying_item: p.carrying_item.clone(),
        })
        .collect();

    let pipes = world
        .pipes
        .iter()
        .map(|pipe| PipeEntityState {
            pipe_id: pipe.pipe_id,
            position: Some(Vector2D { x: pipe.x, y: pipe.y }),
            is_leaking: pipe.is_leaking,
            leak_rate_liters_sec: pipe.leak_rate_liters_sec,
            repair_progress_pct: pipe.repair_progress_pct,
            water_pressure_bar: pipe.water_pressure_bar,
        })
        .collect();

    let valves = world
        .valves
        .iter()
        .map(|v| ValveEntityState {
            valve_id: v.valve_id,
            position: Some(Vector2D { x: v.x, y: v.y }),
            current_destination: v.destination,
            flow_rate_liters_sec: v.flow_rate_liters_sec,
        })
        .collect();

    let plants = world
        .plants
        .iter()
        .map(|pl| TreatmentPlantEntityState {
            plant_id: pl.plant_id,
            position: Some(Vector2D { x: pl.x, y: pl.y }),
            filter_health_pct: pl.filter_health_pct,
            sludge_level_pct: pl.sludge_level_pct,
            purification_rate_lps: pl.purification_rate_lps,
            is_operating: pl.is_operating,
        })
        .collect();

    let water_metrics = WaterMetrics {
        reservoir_level_pct: world.metrics.reservoir_level_pct,
        water_purity_pct: world.metrics.water_purity_pct,
        total_liters_saved: world.metrics.total_liters_saved,
        total_liters_reused: world.metrics.total_liters_reused,
        total_liters_recycled: world.metrics.total_liters_recycled,
    };

    GameWorldState {
        tick: world.tick,
        water_metrics: Some(water_metrics),
        team_score: world.team_score,
        remaining_seconds: world.remaining_seconds,
        players,
        pipes,
        valves,
        plants,
        active_events: Vec::new(),
    }
}

pub fn world_to_proto_snapshot(world: &GameWorld, reconnect_ticket: String) -> GameWorldSnapshot {
    GameWorldSnapshot {
        baseline_tick: world.tick,
        room_id: world.room_id.clone(),
        reconnect_ticket,
        current_state: Some(world_to_proto_state(world)),
        match_duration_seconds: 300,
    }
}

pub fn world_to_proto_match_end(world: &GameWorld) -> MatchEndEvent {
    let player_scores = world
        .players
        .values()
        .map(|p| PlayerScoreBreakdown {
            player_id: p.player_id.clone(),
            username: p.username.clone(),
            role: p.role,
            repairs_done: p.repairs_done,
            water_saved_liters: p.water_saved_liters,
            water_recycled_liters: p.water_recycled_liters,
            individual_points: p.current_score,
        })
        .collect();

    let final_metrics = WaterMetrics {
        reservoir_level_pct: world.metrics.reservoir_level_pct,
        water_purity_pct: world.metrics.water_purity_pct,
        total_liters_saved: world.metrics.total_liters_saved,
        total_liters_reused: world.metrics.total_liters_reused,
        total_liters_recycled: world.metrics.total_liters_recycled,
    };

    MatchEndEvent {
        is_victory: world.is_victory,
        reason: world.finish_reason.clone(),
        final_score: world.team_score,
        final_metrics: Some(final_metrics),
        player_scores,
    }
}
