#!/usr/bin/env python3
"""
Cliente Bot de prueba interactivo gRPC para EcoStream 3R.
Conecta al Gateway (Control Plane) para Login y Matchmaking sin contraseñas,
luego se conecta al Motor Rust (Data Plane) para streaming interactivo a 20 Hz
con acciones 3R autoritativas y telemetría RTT.
"""

import sys
import time
import argparse
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

def run_interactive_client(gateway_host="localhost:50051", engine_host=None, username="EcoBot_01", room_code=""):
    print("=" * 65)
    print(f"[BOT ECOSTREAM-3R] Iniciando cliente bot para usuario: {username}")
    print(f"[CONTROL PLANE] Conectando a Gateway en {gateway_host} via gRPC...")
    print("=" * 65)
    
    gateway_channel = grpc.insecure_channel(gateway_host)
    
    # 1. AUTENTICACIÓN (Sin contraseña - Nickname puro)
    auth_stub = auth_pb2_grpc.AuthServiceStub(gateway_channel)
    print("\n[Paso 1] Autenticando jugador por Nickname...")
    login_resp = auth_stub.Login(auth_pb2.LoginRequest(
        username=username
    ))
    print(f"  -> Login Exitoso! Usuario: {login_resp.user.username} (ID: {login_resp.user.user_id})")
    print(f"  -> Token JWT recibido: {login_resp.token[:25]}...")

    # 2. MATCHMAKING
    match_stub = matchmaking_pb2_grpc.MatchmakingServiceStub(gateway_channel)
    room_id = ""
    room_ticket = ""
    target_engine = engine_host

    if room_code:
        print(f"\n[Paso 2] Uniéndose a sala existente [{room_code}]...")
        join_resp = match_stub.JoinRoom(matchmaking_pb2.JoinRoomRequest(
            token=login_resp.token,
            room_code=room_code,
            selected_role=common_pb2.ROLE_GENERALIST
        ))
        room_id = join_resp.room.room_id
        room_ticket = join_resp.room_ticket
        if not target_engine and join_resp.room.simulation_endpoint:
            target_engine = join_resp.room.simulation_endpoint
        print(f"  -> Unido a Sala! [{join_resp.room.room_code}] - {join_resp.room.room_name}")
    else:
        print("\n[Paso 2] Creando nueva sala multijugador...")
        room_resp = match_stub.CreateRoom(matchmaking_pb2.CreateRoomRequest(
            token=login_resp.token,
            room_name="Operacion Presa Hidroelectrica",
            selected_role=common_pb2.ROLE_HYDRAULIC_ENGINEER,
            max_players=4
        ))
        room_id = room_resp.room.room_id
        room_ticket = room_resp.room_ticket
        if not target_engine and room_resp.room.simulation_endpoint:
            target_engine = room_resp.room.simulation_endpoint
        print(f"  -> Sala Creada! Código: [{room_resp.room.room_code}] - {room_resp.room.room_name}")

    if not target_engine:
        target_engine = "localhost:50052"

    print(f"  -> RoomTicket HMAC recibido: {room_ticket[:30]}...")
    print(f"  -> Endpoint del Motor de Simulación: {target_engine}")

    # 3. STREAMING DE JUEGO A 20 HZ CON ACCIONES 3R EN MOTOR RUST
    print(f"\n[DATA PLANE] Conectando a Motor de Simulación en {target_engine}...")
    engine_channel = grpc.insecure_channel(target_engine)
    gameplay_stub = gameplay_pb2_grpc.GameSimulationServiceStub(engine_channel)

    print("\n[Paso 3] Iniciando Game Loop autoritativo a 20 Ticks/segundo...")
    print("-----------------------------------------------------------------")

    def client_stream_generator():
        # Secuencia de acciones 3R autoritativas
        actions = [
            ("1. REDUCIR (Reparar Fuga Tubería #1)", gameplay_pb2.PlayerAction(
                action_id=1, repair_pipe=gameplay_pb2.RepairPipeAction(pipe_id=1, repair_progress_delta=50.0)
            )),
            ("2. REUSAR (Desviar Aguas Grises a Riego)", gameplay_pb2.PlayerAction(
                action_id=2, divert_valve=gameplay_pb2.DivertValveAction(valve_id=1, destination=gameplay_pb2.DESTINATION_IRRIGATION)
            )),
            ("3. RECICLAR (Cargar Filtros UV Planta)", gameplay_pb2.PlayerAction(
                action_id=3, operate_recycle=gameplay_pb2.OperateRecycleAction(plant_id=1, operation=gameplay_pb2.OperateRecycleAction.RECYCLE_OP_LOAD_FILTER)
            )),
            ("Mover Avatar Dirección Normalizada (dx=0.71, dy=-0.71)", gameplay_pb2.PlayerAction(
                action_id=4, move=gameplay_pb2.MoveAction(direction_x=0.707, direction_y=-0.707)
            )),
            ("1. REDUCIR (Sellar Fuga Tubería #2)", gameplay_pb2.PlayerAction(
                action_id=5, repair_pipe=gameplay_pb2.RepairPipeAction(pipe_id=2, repair_progress_delta=100.0)
            )),
            ("3. RECICLAR (Activar Bomba Filtrado)", gameplay_pb2.PlayerAction(
                action_id=6, operate_recycle=gameplay_pb2.OperateRecycleAction(plant_id=1, operation=gameplay_pb2.OperateRecycleAction.RECYCLE_OP_BOOST_PUMP)
            )),
        ]

        for i, (desc, act) in enumerate(actions):
            t_now_ms = int(time.time() * 1000)
            msg = gameplay_pb2.ClientStreamMessage(
                room_id=room_id,
                player_id=login_resp.user.user_id,
                client_tick=i + 1,
                room_ticket=room_ticket, # Autenticación de sala autoritativa HMAC
                action=act,
                ping=common_pb2.PingMessage(client_timestamp_ms=t_now_ms, sequence_id=i+1)
            )
            print(f"  [Bot -> Motor Rust | Tick #{i+1}] Acción: {desc}")
            yield msg
            time.sleep(0.05) # 50ms por tick (20 Hz)

    responses = gameplay_stub.StreamGame(client_stream_generator())
    for resp in responses:
        if resp.HasField("world_state"):
            ws = resp.world_state
            print(f"  [Motor Rust -> Bot | Tick #{resp.server_tick}] Embalse: {ws.water_metrics.reservoir_level_pct:.1f}% | Pureza: {ws.water_metrics.water_purity_pct:.1f}% | Ahorro: {ws.water_metrics.total_liters_saved:.0f} L | Score: {ws.team_score}")
        if resp.HasField("pong"):
            rtt = int(time.time() * 1000) - resp.pong.echo_client_timestamp_ms
            print(f"      |-- [Telemetría RTT] Latencia: {rtt} ms (Óptimo)")

    print("-----------------------------------------------------------------")
    print("\n[SUCCESS] Prueba de ciclo completo de vida gRPC completada exitosamente!")
    gateway_channel.close()
    engine_channel.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bot de Prueba gRPC para EcoStream-3R")
    parser.add_argument("--gateway", default="localhost:50051", help="Host gRPC del Gateway (Control Plane)")
    parser.add_argument("--engine", default="", help="Host gRPC del Motor (Data Plane)")
    parser.add_argument("--username", default="EcoBot_01", help="Nombre de usuario / Nickname")
    parser.add_argument("--room", default="", help="Código de sala a unirse (si está vacío, crea una)")
    args = parser.parse_args()

    run_interactive_client(
        gateway_host=args.gateway,
        engine_host=args.engine if args.engine else None,
        username=args.username,
        room_code=args.room
    )
