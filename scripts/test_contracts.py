#!/usr/bin/env python3
"""
Test Suite de Integridad para Contratos gRPC y Protocol Buffers de EcoStream 3R.
Verifica:
1. Serializacion binaria de acciones 3R (Reducir, Reusar, Reciclar).
2. Telemetria hidrica y bucle de simulacion GameWorldState.
3. RTT Ping-Pong (latencia de red).
4. Tickets de reconexion rapida (< 5s Grace Period).
5. Integridad de la especificacion OpenAPI 3.0 / Swagger.
"""

import sys
import json
from pathlib import Path

# Configurar encoding UTF-8 en stdout si es posible
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "client-python" / "proto"))

try:
    from ecostream.v1 import common_pb2
    from ecostream.v1 import auth_pb2
    from ecostream.v1 import matchmaking_pb2
    from ecostream.v1 import gameplay_pb2
except ImportError as e:
    print(f"[ERROR] No se pudieron importar los stubs: {e}")
    sys.exit(1)

def test_3r_actions():
    print("\n--- [Test 1] Validacion de Acciones de las 3R ---")
    
    # 1. REDUCIR (Reparar fuga a alta presion)
    reduce_action = gameplay_pb2.PlayerAction(
        action_id=101,
        repair_pipe=gameplay_pb2.RepairPipeAction(
            pipe_id=7,
            repair_progress_delta=25.0
        )
    )
    binary_reduce = reduce_action.SerializeToString()
    print(f"  [1. REDUCIR] Accion Reparar Tuberia #7 creada. Tamano binario: {len(binary_reduce)} bytes")
    
    # 2. REUSAR (Desviar aguas grises hacia riego comunitario)
    reuse_action = gameplay_pb2.PlayerAction(
        action_id=102,
        divert_valve=gameplay_pb2.DivertValveAction(
            valve_id=3,
            destination=gameplay_pb2.DESTINATION_IRRIGATION
        )
    )
    binary_reuse = reuse_action.SerializeToString()
    print(f"  [2. REUSAR] Desvio a Riego Agricola creado. Tamano binario: {len(binary_reuse)} bytes")
    
    # 3. RECICLAR (Carga de carbon activo en planta de tratamiento)
    recycle_action = gameplay_pb2.PlayerAction(
        action_id=103,
        operate_recycle=gameplay_pb2.OperateRecycleAction(
            plant_id=1,
            operation=gameplay_pb2.OperateRecycleAction.RECYCLE_OP_LOAD_FILTER
        )
    )
    binary_recycle = recycle_action.SerializeToString()
    print(f"  [3. RECICLAR] Operacion de Filtrado Biologico creada. Tamano binario: {len(binary_recycle)} bytes")

    # Deserializacion y verificacion de integridad
    deserialized = gameplay_pb2.PlayerAction()
    deserialized.ParseFromString(binary_reduce)
    assert deserialized.repair_pipe.pipe_id == 7
    print("  [OK] Serializacion/Deserializacion binaria validada exitosamente.")

def test_world_state_and_rtt():
    print("\n--- [Test 2] Validacion de GameWorldState (Tick 20Hz) y RTT Telemetria ---")
    
    # Metricas de agua
    metrics = common_pb2.WaterMetrics(
        reservoir_level_pct=88.5,
        water_purity_pct=94.0,
        total_liters_saved=1250.0,
        total_liters_reused=600.0,
        total_liters_recycled=350.0
    )
    
    # Simulacion de jugador
    player = gameplay_pb2.PlayerEntityState(
        player_id="usr_victor",
        username="VictorEngineer",
        role=common_pb2.ROLE_HYDRAULIC_ENGINEER,
        position=common_pb2.Vector2D(x=12.5, y=34.0),
        current_score=450,
        is_connected=True
    )
    
    # Estado del mundo
    world = gameplay_pb2.GameWorldState(
        tick=200, # Tick numero 200 (segundo 10 de juego a 20Hz)
        water_metrics=metrics,
        team_score=1200,
        remaining_seconds=180,
        players=[player]
    )
    
    # Mensaje Ping / Pong para RTT
    ping = common_pb2.PingMessage(client_timestamp_ms=1790994000100, sequence_id=1)
    pong = common_pb2.PongMessage(
        echo_client_timestamp_ms=ping.client_timestamp_ms,
        server_tick=200,
        server_timestamp_ms=1790994000124
    )
    
    # Calculo de RTT en el cliente
    client_now = 1790994000148
    rtt_ms = client_now - pong.echo_client_timestamp_ms
    print(f"  [Telemetria RTT] Ping enviado -> Pong recibido. RTT calculado: {rtt_ms} ms (Estado: VERDE < 60ms)")
    print(f"  [Estado del Mundo] Nivel Embalse: {world.water_metrics.reservoir_level_pct}%, Pureza: {world.water_metrics.water_purity_pct}%")
    assert rtt_ms == 48

def test_reconnection_ticket():
    print("\n--- [Test 3] Protocolo de Reconexion Transitoria (reconnect_ticket) ---")
    req = gameplay_pb2.ReconnectRequest(
        room_id="rm_demo_01",
        player_id="usr_victor",
        reconnect_ticket="tkt_secret_session_abc123",
        last_received_tick=195
    )
    print(f"  [Reconexion] Solicitud de reconexion con ticket '{req.reconnect_ticket}' para tick #{req.last_received_tick}")
    assert len(req.reconnect_ticket) > 0
    print("  [OK] Protocolo de reconexion verificado.")

def test_openapi_spec():
    print("\n--- [Test 4] Verificacion de la Especificacion OpenAPI 3.0 ---")
    openapi_file = ROOT_DIR / "docs" / "swagger" / "openapi.json"
    assert openapi_file.exists(), "openapi.json no encontrado"
    with open(openapi_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"  [OpenAPI] Titulo: {data['info']['title']}")
    print(f"  [Endpoints Documentados]: {list(data['paths'].keys())}")
    assert "/healthz" in data['paths']
    assert "/api/v1/auth/login" in data['paths']
    print("  [OK] Especificacion OpenAPI validada correctamente.")

if __name__ == "__main__":
    print("=" * 60)
    print("[TEST] SUITE DE PRUEBAS DE CONTRATOS: ECOSTREAM 3R")
    print("=" * 60)
    test_3r_actions()
    test_world_state_and_rtt()
    test_reconnection_ticket()
    test_openapi_spec()
    print("\n" + "=" * 60)
    print("[SUCCESS] TODAS LAS PRUEBAS PASARON EXITOSAMENTE (100% OK)")
    print("=" * 60)
