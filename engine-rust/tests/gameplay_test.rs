use engine_rust::game::world::{GameWorld, MAP_HEIGHT};

#[test]
fn test_authoritative_movement_validation() {
    let mut world = GameWorld::new("rm_test_1".to_string(), 1);
    world.add_or_update_player("usr_plumber".to_string(), "PlumberHero".to_string(), 1);

    let initial_x = world.players.get("usr_plumber").unwrap().x;
    let initial_y = world.players.get("usr_plumber").unwrap().y;
    let speed = world.players.get("usr_plumber").unwrap().speed;

    // Movimiento hacia la derecha normalizado: dx = 1.0, dy = 0.0, dt = 0.05
    world.apply_move("usr_plumber", 1.0, 0.0, 0.05);

    let current_x = world.players.get("usr_plumber").unwrap().x;
    let current_y = world.players.get("usr_plumber").unwrap().y;
    assert!(current_x > initial_x, "La posición X debe aumentar hacia la derecha");
    assert_eq!(current_y, initial_y, "La posición Y no debe cambiar");

    // Intento de Speedhack con vector sobredimensionado dx = 100.0, dy = 100.0
    // El motor autoritativo DEBE normalizar el vector a longitud <= 1.0
    let pre_hack_x = current_x;
    world.apply_move("usr_plumber", 100.0, 0.0, 0.05);
    let post_hack_x = world.players.get("usr_plumber").unwrap().x;

    let expected_max_delta = speed * 0.05 + 0.01;
    let actual_delta = post_hack_x - pre_hack_x;
    assert!(
        actual_delta <= expected_max_delta,
        "Anti-speedhack falló: avance real {} superó máximo permitido {}",
        actual_delta,
        expected_max_delta
    );
}

#[test]
fn test_movement_clamped_to_boundaries() {
    let mut world = GameWorld::new("rm_test_2".to_string(), 1);
    world.add_or_update_player("usr_1".to_string(), "P1".to_string(), 4);

    // Intentar mover hacia la izquierda indefinidamente
    for _ in 0..500 {
        world.apply_move("usr_1", -1.0, 0.0, 0.1);
    }

    let p = world.players.get("usr_1").unwrap();
    assert!(p.x >= 20.0, "Jugador no debe salir por el borde izquierdo del mapa: x={}", p.x);

    // Intentar mover hacia abajo indefinidamente
    for _ in 0..500 {
        world.apply_move("usr_1", 0.0, 1.0, 0.1);
    }
    let p = world.players.get("usr_1").unwrap();
    assert!(p.y <= MAP_HEIGHT - 20.0, "Jugador no debe salir por el borde inferior del mapa: y={}", p.y);
}

#[test]
fn test_3r_reducir_pipe_repair() {
    let mut world = GameWorld::new("rm_test_3".to_string(), 1);
    world.add_or_update_player("usr_plumber".to_string(), "Hero".to_string(), 1);

    // Ubicar al jugador cerca de la tubería 1 (x: 180, y: 150)
    let p = world.players.get_mut("usr_plumber").unwrap();
    p.x = 185.0;
    p.y = 155.0;

    // Verificar que tubería 1 gotea inicialmente
    assert!(world.pipes[0].is_leaking);

    // Reparar durante varias iteraciones
    for _ in 0..100 {
        world.apply_repair_pipe("usr_plumber", 1, 0.05);
    }

    // La fuga debe haber sido reparada
    assert!(!world.pipes[0].is_leaking, "Tubería debe estar reparada");
    assert_eq!(world.pipes[0].repair_progress_pct, 100.0);
    assert!(world.metrics.total_liters_saved > 0.0, "Debe acumular agua ahorrada");
    assert!(world.team_score > 0, "Debe premiar con puntaje de equipo");
}

#[test]
fn test_3r_reusar_valve_diverting() {
    let mut world = GameWorld::new("rm_test_4".to_string(), 1);
    world.add_or_update_player("usr_eng".to_string(), "Eng".to_string(), 2);

    // Válvula 1 en (350, 200) apunta a cloaca (1)
    let p = world.players.get_mut("usr_eng").unwrap();
    p.x = 355.0;
    p.y = 205.0;

    assert_eq!(world.valves[0].destination, 1);

    // Desviar a Riego agrícola (2)
    let ok = world.apply_divert_valve("usr_eng", 1, 2);
    assert!(ok, "Debe permitir desviar válvula dentro de rango");
    assert_eq!(world.valves[0].destination, 2);

    // Actualizar mundo varios ticks y comprobar incremento de litros reusados
    for _ in 0..20 {
        world.update(0.05);
    }
    assert!(world.metrics.total_liters_reused > 0.0, "Debe contabilizar litros reusados");
}

#[test]
fn test_world_water_depletion_and_game_over() {
    let mut world = GameWorld::new("rm_test_5".to_string(), 3); // Dificultad alta

    // Forzar embalse bajo
    world.metrics.reservoir_level_pct = 0.5;

    // Actualizar varios ticks hasta que el embalse se agote
    for _ in 0..100 {
        world.update(0.05);
        if world.is_finished {
            break;
        }
    }

    assert!(world.is_finished, "Partida debe haber finalizado");
    assert!(!world.is_victory, "Debe ser derrota por agotamiento de embalse");
    assert_eq!(world.metrics.reservoir_level_pct, 0.0);
}
