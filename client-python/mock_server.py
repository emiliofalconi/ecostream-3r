#!/usr/bin/env python3
"""
Servidor Mock gRPC en tiempo real para EcoStream 3R.
Permite simular el Gateway y el Motor de Simulación Rust (20 Hz) para pruebas y desarrollo.
"""

import sys
import time
from concurrent import futures
from pathlib import Path

# Añadir stubs de proto al path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "client-python" / "proto"))

import grpc
from ecostream.v1 import common_pb2
from ecostream.v1 import auth_pb2
from ecostream.v1 import auth_pb2_grpc
from ecostream.v1 import matchmaking_pb2
from ecostream.v1 import matchmaking_pb2_grpc
from ecostream.v1 import gameplay_pb2
from ecostream.v1 import gameplay_pb2_grpc

class AuthServiceServicer(auth_pb2_grpc.AuthServiceServicer):
    def Login(self, request, context):
        print(f"[AUTH] Login recibido para usuario: {request.username_or_email}")
        return auth_pb2.LoginResponse(
            success=True,
            message="Inicio de sesion exitoso",
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock_token_victor",
            user=auth_pb2.UserProfile(
                user_id="usr_victor_admin",
                username="VictorAdmin",
                email="victor@ecostream.ucab.ve",
                default_role=common_pb2.ROLE_HYDRAULIC_ENGINEER,
                games_played=10,
                games_won=8,
                total_eco_score=4500.0
            ),
            expires_at_unix=int(time.time()) + 86400
        )

    def Register(self, request, context):
        print(f"[AUTH] Registro de nuevo usuario: {request.username}")
        return auth_pb2.RegisterResponse(
            success=True,
            message="Usuario registrado exitosamente",
            token="mock_token_registered",
            user=auth_pb2.UserProfile(
                user_id="usr_new_player",
                username=request.username,
                email=request.email,
                default_role=request.default_role
            ),
            expires_at_unix=int(time.time()) + 86400
        )

class MatchmakingServiceServicer(matchmaking_pb2_grpc.MatchmakingServiceServicer):
    def CreateRoom(self, request, context):
        print(f"[MATCHMAKING] Creando sala: '{request.room_name}' (Max: {request.max_players})")
        return matchmaking_pb2.CreateRoomResponse(
            success=True,
            message="Sala creada correctamente",
            room=matchmaking_pb2.RoomInfo(
                room_id="rm_demo_01",
                room_code="AGUA42",
                room_name=request.room_name,
                status=matchmaking_pb2.ROOM_STATUS_WAITING,
                max_players=request.max_players,
                simulation_endpoint="localhost:50051",
                created_at_unix=int(time.time()),
                difficulty_level=1
            ),
            room_ticket="tkt_sim_token_secret_42"
        )

    def QuickMatch(self, request, context):
        print(f"[MATCHMAKING] Busqueda de partida rapida (Rol: {request.preferred_role})")
        return matchmaking_pb2.QuickMatchResponse(
            success=True,
            message="Emparejado con sala existente",
            room=matchmaking_pb2.RoomInfo(
                room_id="rm_demo_01",
                room_code="AGUA42",
                room_name="Embalse Colaborativo",
                status=matchmaking_pb2.ROOM_STATUS_STARTING,
                max_players=4,
                simulation_endpoint="localhost:50051"
            ),
            room_ticket="tkt_quick_match_42"
        )

import random
import threading
import argparse

class GameRoom:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.tick = 0
        self.reservoir = 100.0
        self.purity = 96.0
        self.saved_liters = 0.0
        self.reused_liters = 0.0
        self.recycled_liters = 0.0
        self.team_score = 0
        self.pipes_state = {
            1: {"is_leaking": False, "leak_rate": 0.0, "progress": 100.0, "pressure": 3.5},
            2: {"is_leaking": True,  "leak_rate": 8.5, "progress": 0.0,   "pressure": 4.2},
            3: {"is_leaking": False, "leak_rate": 0.0, "progress": 100.0, "pressure": 3.8},
        }
        self.players = {}  # player_id: {"x": float, "y": float, "username": str, "last_seen": float, "role": int}
        self.active_event_type = None
        self.active_event_timer = 0
        self.active_event_title = ""
        self.lock = threading.Lock()

class GameSimulationServiceServicer(gameplay_pb2_grpc.GameSimulationServiceServicer):
    def __init__(self):
        self.rooms = {}
        self.lock = threading.Lock()

    def get_room(self, room_id: str) -> GameRoom:
        with self.lock:
            if room_id not in self.rooms:
                self.rooms[room_id] = GameRoom(room_id)
            return self.rooms[room_id]

    def StreamGame(self, request_iterator, context):
        print(f"[{time.strftime('%H:%M:%S')}] [GAMEPLAY] Streaming bidireccional HTTP/2 conectado con nuevo cliente (20 Hz)!")
        client_player_id = None
        client_room_id = None

        for client_msg in request_iterator:
            client_player_id = client_msg.player_id
            client_room_id = client_msg.room_id
            room = self.get_room(client_room_id)

            with room.lock:
                room.tick += 1
                tick = room.tick

                # Registrar o actualizar posición del jugador en la sala compartida
                if client_player_id not in room.players:
                    room.players[client_player_id] = {
                        "x": 380.0,
                        "y": 320.0,
                        "username": client_player_id,
                        "last_seen": time.time(),
                        "score": 0
                    }
                    print(f"  -> [SALA '{client_room_id}'] Jugador '{client_player_id}' se unió a la sesión multijugador.")

                player_data = room.players[client_player_id]
                player_data["last_seen"] = time.time()

                # Emitir snapshot inicial con ticket de sesión en el tick 1
                if tick == 1 or client_msg.client_tick == 1:
                    tkt = f"tkt_reconn_{client_player_id}_{tick}"
                    init_snap = gameplay_pb2.ServerStreamMessage(
                        server_tick=tick,
                        server_timestamp_unix_ms=int(time.time() * 1000),
                        initial_snapshot=gameplay_pb2.GameWorldSnapshot(
                            baseline_tick=tick,
                            room_id=client_room_id,
                            reconnect_ticket=tkt,
                            match_duration_seconds=180
                        )
                    )
                    yield init_snap

                # Procesar acción autoritativa enviada por el cliente
                if client_msg.HasField("action"):
                    action = client_msg.action
                    if action.HasField("move"):
                        player_data["x"] = action.move.target_position.x
                        player_data["y"] = action.move.target_position.y
                    elif action.HasField("repair_pipe"):
                        pid = action.repair_pipe.pipe_id
                        if pid in room.pipes_state and room.pipes_state[pid]["is_leaking"]:
                            room.pipes_state[pid]["is_leaking"] = False
                            room.pipes_state[pid]["progress"] = 100.0
                            room.saved_liters += 75.0
                            room.team_score += 150
                            print(f"  -> [{time.strftime('%H:%M:%S')}] [{client_player_id}] [1. REDUCIR] Tubería #{pid} reparada (+150 pts | +75 L)")
                    elif action.HasField("divert_valve"):
                        room.reused_liters += 25.0
                        room.team_score += 80
                        print(f"  -> [{time.strftime('%H:%M:%S')}] [{client_player_id}] [2. REUSAR] Válvula desviada a huerto agrícola (+80 pts | +25 L)")
                    elif action.HasField("operate_recycle"):
                        room.purity = min(100.0, room.purity + 2.0)
                        room.recycled_liters += 50.0
                        room.team_score += 120
                        print(f"  -> [{time.strftime('%H:%M:%S')}] [{client_player_id}] [3. RECICLAR] Planta de filtrado activada (+120 pts | Pureza: {room.purity:.1f}%)")

                # Fugas periódicas dinámicas cada 250 ticks (~12.5 segundos)
                if tick % 250 == 0:
                    ok_pipes = [p_id for p_id, p_data in room.pipes_state.items() if not p_data["is_leaking"]]
                    if ok_pipes:
                        chosen = random.choice(ok_pipes)
                        room.pipes_state[chosen]["is_leaking"] = True
                        room.pipes_state[chosen]["progress"] = 0.0
                        print(f"  -> [{time.strftime('%H:%M:%S')}] [ALERTA FUGA] ¡Rotura generada en Tubería #{chosen} a presión!")

                # Eventos de Caos Dinámicos cada 400 ticks (~20 segundos)
                if tick % 400 == 0:
                    event_roll = random.choice([1, 2, 4])
                    if event_roll == 1:
                        room.active_event_type = gameplay_pb2.ActiveEvent.EVENT_TYPE_HEATWAVE
                        room.active_event_title = "☀️ ¡Ola de Calor Extrema! Demanda hídrica x2"
                        room.active_event_timer = 200 # 10 segundos
                    elif event_roll == 2:
                        room.active_event_type = gameplay_pb2.ActiveEvent.EVENT_TYPE_MAJOR_BURST
                        room.active_event_title = "🚨 ¡Mega-Rotura a Presión! Fugas críticas"
                        room.active_event_timer = 200
                        for p in room.pipes_state.values():
                            p["is_leaking"] = True
                    elif event_roll == 4:
                        room.active_event_type = gameplay_pb2.ActiveEvent.EVENT_TYPE_RAIN_HARVEST
                        room.active_event_title = "🌧️ ¡Lluvia Torrencial! Captación +20% agua"
                        room.active_event_timer = 200
                        room.reservoir = min(100.0, room.reservoir + 20.0)
                    print(f"  -> [CHAOS EVENT] {room.active_event_title}")

                if room.active_event_timer > 0:
                    room.active_event_timer -= 1
                    if room.active_event_timer == 0:
                        room.active_event_type = None
                        room.active_event_title = ""

                # Simular drenaje hídrico realista (consumo base + fugas activas)
                total_leak_rate = sum(p["leak_rate"] for p in room.pipes_state.values() if p["is_leaking"])
                drain = 0.0035 + (total_leak_rate * 0.0009)
                room.reservoir = max(0.0, room.reservoir - drain)

                # Construir entidades Proto
                proto_pipes = []
                for pid, pdata in room.pipes_state.items():
                    proto_pipes.append(gameplay_pb2.PipeEntityState(
                        pipe_id=pid,
                        position=common_pb2.Vector2D(x=380.0, y=160.0 + (pid - 1) * 60.0),
                        is_leaking=pdata["is_leaking"],
                        leak_rate_liters_sec=pdata["leak_rate"] if pdata["is_leaking"] else 0.0,
                        repair_progress_pct=pdata["progress"],
                        water_pressure_bar=pdata["pressure"]
                    ))

                proto_valves = [
                    gameplay_pb2.ValveEntityState(
                        valve_id=1,
                        position=common_pb2.Vector2D(x=400.0, y=420.0),
                        current_destination=gameplay_pb2.DESTINATION_IRRIGATION,
                        flow_rate_liters_sec=12.0
                    )
                ]

                proto_plants = [
                    gameplay_pb2.TreatmentPlantEntityState(
                        plant_id=1,
                        position=common_pb2.Vector2D(x=800.0, y=380.0),
                        filter_health_pct=95.0,
                        sludge_level_pct=15.0,
                        purification_rate_lps=15.0,
                        is_operating=True
                    )
                ]

                # Lista de todos los jugadores activos en la sala
                proto_players = []
                for pid, p_info in room.players.items():
                    proto_players.append(gameplay_pb2.PlayerEntityState(
                        player_id=pid,
                        username=p_info["username"],
                        position=common_pb2.Vector2D(x=p_info["x"], y=p_info["y"]),
                        current_score=room.team_score,
                        is_connected=True
                    ))

                # Eventos activos
                proto_events = []
                if room.active_event_type:
                    proto_events.append(gameplay_pb2.ActiveEvent(
                        event_id=1,
                        event_type=room.active_event_type,
                        title=room.active_event_title,
                        remaining_seconds=int(room.active_event_timer / 20)
                    ))

                # Construir estado del mundo a 20Hz
                state = gameplay_pb2.GameWorldState(
                    tick=tick,
                    water_metrics=common_pb2.WaterMetrics(
                        reservoir_level_pct=round(room.reservoir, 2),
                        water_purity_pct=round(room.purity, 2),
                        total_liters_saved=room.saved_liters,
                        total_liters_reused=room.reused_liters,
                        total_liters_recycled=room.recycled_liters
                    ),
                    team_score=room.team_score,
                    remaining_seconds=max(0, 180 - int(tick / 20)),
                    pipes=proto_pipes,
                    valves=proto_valves,
                    plants=proto_plants,
                    players=proto_players,
                    active_events=proto_events
                )

                server_msg = gameplay_pb2.ServerStreamMessage(
                    server_tick=tick,
                    server_timestamp_unix_ms=int(time.time() * 1000),
                    world_state=state
                )
                yield server_msg

            # Responde al Ping si viene incluido
            if client_msg.HasField("ping"):
                pong_msg = gameplay_pb2.ServerStreamMessage(
                    server_tick=tick,
                    pong=common_pb2.PongMessage(
                        echo_client_timestamp_ms=client_msg.ping.client_timestamp_ms,
                        server_tick=tick
                    )
                )
                yield pong_msg

    def ReconnectSession(self, request, context):
        print(f"[RECONNECT] Peticion de reconexion recibida para {request.player_id} en sala {request.room_id}")
        if request.reconnect_ticket.startswith("tkt_"):
            snapshot = gameplay_pb2.GameWorldSnapshot(
                baseline_tick=request.last_received_tick + 10,
                room_id=request.room_id,
                reconnect_ticket=request.reconnect_ticket,
                match_duration_seconds=180,
                current_state=gameplay_pb2.GameWorldState(
                    tick=request.last_received_tick + 10,
                    water_metrics=common_pb2.WaterMetrics(
                        reservoir_level_pct=85.5,
                        water_purity_pct=95.0,
                        total_liters_saved=150.0,
                        total_liters_reused=40.0,
                        total_liters_recycled=50.0
                    ),
                    team_score=350,
                    remaining_seconds=150
                )
            )
            return gameplay_pb2.ReconnectResponse(
                success=True,
                message="Reconexión exitosa reconciliada con servidor autoritativo.",
                snapshot=snapshot
            )
        else:
            return gameplay_pb2.ReconnectResponse(
                success=False,
                message="Ticket de reconexión inválido o sesión expirada.",
                snapshot=None
            )

def serve(port=50051):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    auth_pb2_grpc.add_AuthServiceServicer_to_server(AuthServiceServicer(), server)
    matchmaking_pb2_grpc.add_MatchmakingServiceServicer_to_server(MatchmakingServiceServicer(), server)
    gameplay_pb2_grpc.add_GameSimulationServiceServicer_to_server(GameSimulationServiceServicer(), server)

    server.add_insecure_port(f"0.0.0.0:{port}")
    server.start()
    print(f"============================================================")
    print(f"[ECOSTREAM SERVER] Servidor gRPC Mock iniciado en puerto {port}")
    print(f"  - AuthService activo")
    print(f"  - MatchmakingService activo")
    print(f"  - GameSimulationService (20 Hz Loop) activo")
    print(f"============================================================")
    return server

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EcoStream 3R - Servidor Autoritativo gRPC (Multi-Host / Réplicas)")
    parser.add_argument("--port", type=int, default=50051, help="Puerto de escucha gRPC (ej: 50051 para nodo primario, 50052 para réplica secundaria)")
    args = parser.parse_args()

    s = serve(port=args.port)
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        s.stop(0)
        print(f"\n[ECOSTREAM SERVER] Servidor en puerto {args.port} detenido.")
