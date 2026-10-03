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

class GameSimulationServiceServicer(gameplay_pb2_grpc.GameSimulationServiceServicer):
    def StreamGame(self, request_iterator, context):
        print("[GAMEPLAY] Streaming bidireccional HTTP/2 iniciado con el cliente a 20 Hz!")
        tick = 0
        reservoir = 100.0
        purity = 98.0
        saved_liters = 0.0

        for client_msg in request_iterator:
            tick += 1
            
            # Procesar accion del cliente
            if client_msg.HasField("action"):
                action = client_msg.action
                if action.HasField("repair_pipe"):
                    saved_liters += 50.0
                    print(f"  -> [TICK {tick}] Cliente ejecuto: 1. REDUCIR (Reparar Tuberia #{action.repair_pipe.pipe_id})")
                elif action.HasField("divert_valve"):
                    print(f"  -> [TICK {tick}] Cliente ejecuto: 2. REUSAR (Desviar Valvula #{action.divert_valve.valve_id})")
                elif action.HasField("operate_recycle"):
                    purity = min(100.0, purity + 1.5)
                    print(f"  -> [TICK {tick}] Cliente ejecuto: 3. RECICLAR (Planta Filtrado)")

            # Simular drenaje hídrico
            reservoir = max(0.0, reservoir - 0.05)

            # Construir estado del mundo a 20Hz
            state = gameplay_pb2.GameWorldState(
                tick=tick,
                water_metrics=common_pb2.WaterMetrics(
                    reservoir_level_pct=round(reservoir, 2),
                    water_purity_pct=round(purity, 2),
                    total_liters_saved=saved_liters
                ),
                team_score=int(saved_liters * 10),
                remaining_seconds=180
            )

            # Responder con ServerStreamMessage
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
    s = serve()
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        s.stop(0)
        print("\n[ECOSTREAM SERVER] Servidor detenido.")
