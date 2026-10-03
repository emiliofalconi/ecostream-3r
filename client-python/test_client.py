#!/usr/bin/env python3
"""
Cliente de prueba interactivo gRPC para EcoStream 3R.
Conecta al servidor, ejecuta Login, Matchmaking y un streaming interactivo a 20 Hz con acciones 3R y telemetría RTT.
"""

import sys
import time
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

def run_interactive_client(host="localhost:50051"):
    print("=" * 65)
    print(f"[CLIENTE ECOSTREAM] Conectando a {host} via gRPC...")
    print("=" * 65)
    
    channel = grpc.insecure_channel(host)
    
    # 1. AUTENTICACIÓN
    auth_stub = auth_pb2_grpc.AuthServiceStub(channel)
    print("\n[Paso 1] Iniciando sesion...")
    login_resp = auth_stub.Login(auth_pb2.LoginRequest(
        username_or_email="victor@ecostream.ucab.ve",
        password="SuperEcoPass123!"
    ))
    print(f"  -> Login Exitoso! Usuario: {login_resp.user.username} (Puntaje Eco: {login_resp.user.total_eco_score})")
    print(f"  -> Token JWT recibido: {login_resp.token[:25]}...")

    # 2. MATCHMAKING
    match_stub = matchmaking_pb2_grpc.MatchmakingServiceStub(channel)
    print("\n[Paso 2] Creando sala multijugador...")
    room_resp = match_stub.CreateRoom(matchmaking_pb2.CreateRoomRequest(
        token=login_resp.token,
        room_name="Operacion Presa Hidroelectrica",
        selected_role=common_pb2.ROLE_HYDRAULIC_ENGINEER,
        max_players=4
    ))
    print(f"  -> Sala Creada! Codigo de Lobby: [{room_resp.room.room_code}] - Nombre: '{room_resp.room.room_name}'")
    print(f"  -> Ticket de simulación: {room_resp.room_ticket}")

    # 3. STREAMING DE JUEGO A 20 HZ CON ACCIONES 3R
    gameplay_stub = gameplay_pb2_grpc.GameSimulationServiceStub(channel)
    print("\n[Paso 3] Iniciando Game Loop autoritativo a 20 Ticks/segundo...")
    print("-----------------------------------------------------------------")

    def client_stream_generator():
        # Generar 6 ticks de simulación interactiva con acciones de las 3R
        actions = [
            ("1. REDUCIR (Reparar Fuga Tubería #2)", gameplay_pb2.PlayerAction(
                action_id=1, repair_pipe=gameplay_pb2.RepairPipeAction(pipe_id=2, repair_progress_delta=50.0)
            )),
            ("2. REUSAR (Desviar Aguas Grises a Cultivos)", gameplay_pb2.PlayerAction(
                action_id=2, divert_valve=gameplay_pb2.DivertValveAction(valve_id=1, destination=gameplay_pb2.DESTINATION_IRRIGATION)
            )),
            ("3. RECICLAR (Filtrado de Lodos Industriales)", gameplay_pb2.PlayerAction(
                action_id=3, operate_recycle=gameplay_pb2.OperateRecycleAction(plant_id=1, operation=gameplay_pb2.OperateRecycleAction.RECYCLE_OP_LOAD_FILTER)
            )),
            ("Mover Avatar (x=15.0, y=22.5)", gameplay_pb2.PlayerAction(
                action_id=4, move=gameplay_pb2.MoveAction(target_position=common_pb2.Vector2D(x=15.0, y=22.5))
            )),
            ("1. REDUCIR (Sellar Válvula Matriz)", gameplay_pb2.PlayerAction(
                action_id=5, repair_pipe=gameplay_pb2.RepairPipeAction(pipe_id=5, repair_progress_delta=100.0)
            )),
        ]

        for i, (desc, act) in enumerate(actions):
            t_now_ms = int(time.time() * 1000)
            msg = gameplay_pb2.ClientStreamMessage(
                room_id=room_resp.room.room_id,
                player_id=login_resp.user.user_id,
                client_tick=i + 1,
                action=act,
                ping=common_pb2.PingMessage(client_timestamp_ms=t_now_ms, sequence_id=i+1)
            )
            print(f"  [Cliente -> Servidor] Enviando accion: {desc}")
            yield msg
            time.sleep(0.05) # 50ms por tick (20 Hz)

    # Recibir respuestas del servidor Rust en tiempo real
    responses = gameplay_stub.StreamGame(client_stream_generator())
    for resp in responses:
        if resp.HasField("world_state"):
            ws = resp.world_state
            print(f"  [Servidor -> Cliente | Tick #{resp.server_tick}] Embalse: {ws.water_metrics.reservoir_level_pct}% | Pureza: {ws.water_metrics.water_purity_pct}% | Ahorro: {ws.water_metrics.total_liters_saved} L | Score: {ws.team_score}")
        if resp.HasField("pong"):
            rtt = int(time.time() * 1000) - resp.pong.echo_client_timestamp_ms
            print(f"      |-- [Telemetria RTT] Latencia en vivo: {rtt} ms (Estado: OPTIMO)")

    print("-----------------------------------------------------------------")
    print("\n[SUCCESS] Prueba de ciclo completo de vida gRPC completada exitosamente!")
    channel.close()

if __name__ == "__main__":
    run_interactive_client()
