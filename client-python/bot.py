#!/usr/bin/env python3
"""
EcoStream-3R — Cliente Bot Autónomo (Python)
--------------------------------------------
Diseñado para pruebas de carga, simulación de jugadores y verificación continua.

Flujo de Operación:
1. Control Plane (Gateway Go):
   - Login por Nickname (sin contraseña) y emisión de JWT.
   - Matchmaking: Creación o unión a sala y recepción de RoomTicket firmado con HMAC.
2. Data Plane (Motor Rust 20 Hz):
   - Conexión gRPC directa (StreamGame) al SimulationEngine autoritativo.
   - Envío de RoomTicket HMAC en ClientStreamMessage.
   - Inteligencia Artificial 3R (Reducir fugas, Reusar aguas grises, Reciclar aguas servidas).
   - Movimiento autoritativo por vectores direccionales normalizados (Anti-speedhack).
   - Medición de telemetría de latencia RTT (Ping/Pong).
"""

import sys
import os
import time
import math
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path

# Añadir directorio de stubs proto al path
ROOT_DIR = Path(__file__).resolve().parent
PROTO_DIR = ROOT_DIR / "proto"
sys.path.insert(0, str(PROTO_DIR))
sys.path.insert(0, str(ROOT_DIR))

try:
    from discovery import discover_servers
except ImportError:
    discover_servers = None

try:
    import grpc
    from ecostream.v1 import common_pb2
    from ecostream.v1 import gameplay_pb2
    from ecostream.v1 import gameplay_pb2_grpc
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False


# Colores para salida en consola
BOLD = "\033[1m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
RESET = "\033[0m"


class EcoBot:
    def __init__(self, gateway_url="http://localhost:8080", engine_endpoint="", username="EcoBot_01", room_code="", role=4, duration=60):
        self.gateway_url = gateway_url.rstrip("/")
        self.engine_endpoint = engine_endpoint
        self.username = username
        self.room_code = room_code
        self.role = role
        self.duration = duration

        # Estado de sesión
        self.jwt_token = ""
        self.user_id = ""
        self.room_id = ""
        self.room_ticket = ""

        # Posición del jugador (sincronizada desde el servidor)
        self.pos_x = 380.0
        self.pos_y = 320.0

        # Telemetría de partida
        self.current_tick = 0
        self.reservoir_pct = 100.0
        self.purity_pct = 95.0
        self.team_score = 0
        self.rtt_ms = 0
        self.repairs_done = 0
        self.reuses_done = 0
        self.recycles_done = 0

    def step_1_authenticate(self) -> bool:
        """Autenticación rápida por Nickname (sin contraseñas) vía REST Gateway"""
        print(f"\n{BOLD}{CYAN}--- [PASO 1] Autenticación de Bot en Gateway ---{RESET}")
        url = f"{self.gateway_url}/api/v1/auth/login"
        payload = json.dumps({"username": self.username}).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode())
                self.jwt_token = data.get("token") or data.get("access_token")
                user = data.get("user", {})
                self.user_id = user.get("user_id", f"usr_{self.username}")
                print(f"  {GREEN}✓ Login exitoso:{RESET} Usuario '{self.username}' | ID: {self.user_id}")
                print(f"  {GREEN}✓ JWT emitido:{RESET} {self.jwt_token[:30]}...")
                return True
        except Exception as e:
            print(f"  {RED}✗ Error en autenticación con {url}: {e}{RESET}")
            return False

    def step_2_matchmaking(self) -> bool:
        """Creación o unión a sala para obtener RoomTicket HMAC y endpoint del motor"""
        print(f"\n{BOLD}{CYAN}--- [PASO 2] Matchmaking y Obtención de RoomTicket ---{RESET}")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.jwt_token}"
        }

        try:
            if self.room_code:
                # Unirse a sala existente
                url = f"{self.gateway_url}/api/v1/rooms/join"
                payload = json.dumps({
                    "room_code": self.room_code,
                    "role": self.role
                }).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    data = json.loads(resp.read().decode())
                    room = data.get("room", {})
                    self.room_id = room.get("id") or room.get("room_id")
                    self.room_ticket = data.get("room_ticket", "")
                    if not self.engine_endpoint:
                        self.engine_endpoint = room.get("simulation_endpoint", "localhost:50052")
                    print(f"  {GREEN}✓ Unido a sala existente:{RESET} [{self.room_code}] - ID: {self.room_id}")
            else:
                # Crear nueva sala
                url = f"{self.gateway_url}/api/v1/rooms/create"
                payload = json.dumps({
                    "room_name": f"Operacion_{self.username}",
                    "role": self.role,
                    "max_players": 4,
                    "difficulty": 1
                }).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    data = json.loads(resp.read().decode())
                    room = data.get("room", {})
                    self.room_id = room.get("id") or room.get("room_id")
                    self.room_code = room.get("room_code", "AUTO")
                    self.room_ticket = data.get("room_ticket", "")
                    if not self.engine_endpoint:
                        self.engine_endpoint = room.get("simulation_endpoint", "localhost:50052")
                    print(f"  {GREEN}✓ Sala creada exitosamente:{RESET} Código [{self.room_code}] | ID: {self.room_id}")

            print(f"  {GREEN}✓ RoomTicket HMAC:{RESET} {self.room_ticket[:32]}... (Firma criptográfica)")
            print(f"  {GREEN}✓ Endpoint del Motor Rust:{RESET} {self.engine_endpoint}")
            return True
        except Exception as e:
            print(f"  {RED}✗ Error en matchmaking: {e}{RESET}")
            return False

    def step_3_stream_simulation(self):
        """Conexión gRPC bidireccional a 20 Hz con el motor de simulación Rust"""
        print(f"\n{BOLD}{CYAN}--- [PASO 3] Streaming Autoritativo 20 Hz (Data Plane Rust) ---{RESET}")
        if not GRPC_AVAILABLE:
            print(f"{RED}Error: El paquete 'grpc' no está instalado en este entorno.{RESET}")
            print(f"Para habilitar el streaming nativo de gRPC, ejecuta:")
            print(f"  pip install -r client-python/requirements.txt")
            return False

        use_tls = ":443" in self.engine_endpoint or self.gateway_url.startswith("https://")
        print(f"  Conectando a {self.engine_endpoint} (TLS={use_tls})...")

        if use_tls:
            creds = grpc.ssl_channel_credentials()
            channel = grpc.secure_channel(self.engine_endpoint, creds)
        else:
            channel = grpc.insecure_channel(self.engine_endpoint)

        stub = gameplay_pb2_grpc.GameSimulationServiceStub(channel)

        # Estado compartido para generador de cliente
        pipes_state = []
        valves_state = []
        plants_state = []
        running = True
        start_time = time.time()

        def request_generator():
            client_tick = 0
            while running and (time.time() - start_time < self.duration):
                client_tick += 1
                t_now = int(time.time() * 1000)

                # Decisión de IA autónoma
                action = self._decide_ai_action(client_tick, pipes_state, valves_state, plants_state)

                msg = gameplay_pb2.ClientStreamMessage(
                    room_id=self.room_id,
                    player_id=self.user_id,
                    client_tick=client_tick,
                    room_ticket=self.room_ticket, # Validación HMAC obligatoria en Rust
                    action=action,
                    ping=common_pb2.PingMessage(client_timestamp_ms=t_now, sequence_id=client_tick)
                )
                yield msg
                time.sleep(0.05) # 50 ms = 20 Hz exactos

        try:
            responses = stub.StreamGame(request_generator())
            print(f"  {GREEN}{BOLD}✓ StreamGame conectado exitosamente a 20 Ticks/segundo!{RESET}\n")

            for resp in responses:
                self.current_tick = resp.server_tick

                if resp.HasField("world_state"):
                    ws = resp.world_state
                    pipes_state = list(ws.pipes)
                    valves_state = list(ws.valves)
                    plants_state = list(ws.plants)

                    if ws.water_metrics:
                        self.reservoir_pct = ws.water_metrics.reservoir_level_pct
                        self.purity_pct = ws.water_metrics.water_purity_pct
                    self.team_score = ws.team_score

                    # Actualizar posición del bot con las coordenadas autoritativas de Rust
                    for p in ws.players:
                        if p.player_id == self.user_id and p.position:
                            self.pos_x = p.position.x
                            self.pos_y = p.position.y

                    # Reporte de telemetría en consola cada 20 ticks (1 segundo)
                    if self.current_tick % 20 == 0:
                        leaks_count = sum(1 for pipe in pipes_state if pipe.is_leaking)
                        print(
                            f"  [{BOLD}Tick {self.current_tick:04d}{RESET} | RTT: {GREEN}{self.rtt_ms:02d}ms{RESET}] "
                            f"Embalse: {CYAN}{self.reservoir_pct:5.1f}%{RESET} | "
                            f"Pureza: {GREEN}{self.purity_pct:5.1f}%{RESET} | "
                            f"Score: {YELLOW}{self.team_score:4d}{RESET} | "
                            f"Fugas activas: {RED if leaks_count > 0 else GREEN}{leaks_count}{RESET} | "
                            f"Pos: ({self.pos_x:5.1f}, {self.pos_y:5.1f})"
                        )

                if resp.HasField("pong"):
                    self.rtt_ms = int(time.time() * 1000) - resp.pong.echo_client_timestamp_ms

                if time.time() - start_time >= self.duration:
                    print(f"\n{YELLOW}Tiempo límite de simulación alcanzado ({self.duration}s). Finalizando bot...{RESET}")
                    running = False
                    break

            channel.close()
            print(f"\n{GREEN}{BOLD}=== RESUMEN DE SESIÓN DEL BOT ==={RESET}")
            print(f"  - Ticks completados: {self.current_tick}")
            print(f"  - Score final del equipo: {self.team_score}")
            print(f"  - Nivel de embalse final: {self.reservoir_pct:.1f}%")
            print(f"  - Pureza hídrica final: {self.purity_pct:.1f}%")
            print(f"  - Acciones ejecutadas: {self.repairs_done} reparaciones, {self.reuses_done} desvíos, {self.recycles_done} filtrados\n")
            return True

        except Exception as e:
            print(f"  {RED}✗ Desconexión o error en stream: {e}{RESET}")
            return False

    def _decide_ai_action(self, tick, pipes, valves, plants):
        """Lógica de IA: Prioriza Reducir fugas, Reusar aguas y Reciclar"""
        # 1. REDUCIR: Buscar fugas activas
        leaking_pipes = [p for p in pipes if p.is_leaking]
        if leaking_pipes:
            target = leaking_pipes[0]
            # Coordenadas conocidas de tuberías en mapa
            tx = target.position.x if target.position and target.position.x > 0 else 420.0
            ty = target.position.y if target.position and target.position.y > 0 else (180.0 + (target.pipe_id - 1) * 60.0)

            dx = tx - self.pos_x
            dy = ty - self.pos_y
            dist = math.hypot(dx, dy)

            # Si está lejos (> 45px), moverse hacia la fuga con vector normalizado
            if dist > 45.0:
                return gameplay_pb2.PlayerAction(
                    action_id=tick,
                    move=gameplay_pb2.MoveAction(
                        direction_x=dx / dist,
                        direction_y=dy / dist
                    )
                )
            else:
                # En proximidad: reparar fuga (Reducir)
                self.repairs_done += 1
                return gameplay_pb2.PlayerAction(
                    action_id=tick,
                    repair_pipe=gameplay_pb2.RepairPipeAction(
                        pipe_id=target.pipe_id,
                        repair_progress_delta=50.0
                    )
                )

        # 2. REUSAR: Desviar válvulas hacia huertos periódicamente
        if tick % 40 == 0 and valves:
            self.reuses_done += 1
            return gameplay_pb2.PlayerAction(
                action_id=tick,
                divert_valve=gameplay_pb2.DivertValveAction(
                    valve_id=1,
                    destination=gameplay_pb2.DESTINATION_IRRIGATION
                )
            )

        # 3. RECICLAR: Cargar reactivos y activar bomba de filtrado
        if tick % 60 == 0 and plants:
            self.recycles_done += 1
            op = gameplay_pb2.OperateRecycleAction.RECYCLE_OP_LOAD_FILTER if (tick % 120 == 0) else gameplay_pb2.OperateRecycleAction.RECYCLE_OP_BOOST_PUMP
            return gameplay_pb2.PlayerAction(
                action_id=tick,
                operate_recycle=gameplay_pb2.OperateRecycleAction(
                    plant_id=1,
                    operation=op
                )
            )

        # Movimiento de patrulla preventiva si todo está en orden
        patrol_angle = (tick % 100) * (2.0 * math.pi / 100.0)
        return gameplay_pb2.PlayerAction(
            action_id=tick,
            move=gameplay_pb2.MoveAction(
                direction_x=math.cos(patrol_angle) * 0.5,
                direction_y=math.sin(patrol_angle) * 0.5
            )
        )

    def run(self):
        """Ejecuta el ciclo de vida completo del bot"""
        print(f"\n{BOLD}{GREEN}==================================================================={RESET}")
        print(f"{BOLD}{GREEN}  EcoStream-3R: Bot Autónomo de Simulación y Pruebas 20 Hz         {RESET}")
        print(f"{BOLD}{GREEN}==================================================================={RESET}")
        print(f"  Usuario Bot : {self.username}")
        print(f"  Gateway     : {self.gateway_url}")
        print(f"  Duración    : {self.duration} segundos")

        if not self.step_1_authenticate():
            return False

        if not self.step_2_matchmaking():
            return False

        return self.step_3_stream_simulation()


def main():
    parser = argparse.ArgumentParser(description="Bot Autónomo para EcoStream-3R")
    parser.add_argument("--env", choices=["auto", "local", "cloud"], default="auto",
                        help="Entorno de ejecución: 'auto' (mDNS local con fallback a Render), 'local', o 'cloud'")
    parser.add_argument("--gateway", default="", help="URL del Gateway REST (omite para detección automática)")
    parser.add_argument("--engine", default="", help="Endpoint gRPC del motor Rust (omite para detección automática)")
    parser.add_argument("--username", default="EcoBot_01", help="Nombre de usuario / Nickname para el bot")
    parser.add_argument("--room", default="", help="Código de sala a unirse (si está vacío, crea una sala automáticamente)")
    parser.add_argument("--role", type=int, default=4, help="Rol del jugador: 1=Plumber, 2=Hydraulic, 3=Chemical, 4=Generalist")
    parser.add_argument("--duration", type=int, default=60, help="Duración de la sesión del bot en segundos")

    args = parser.parse_args()

    gateway_url = args.gateway
    engine_endpoint = args.engine

    if not gateway_url:
        if args.env == "local":
            gateway_url = "http://localhost:8080"
            if not engine_endpoint:
                engine_endpoint = "localhost:50052"
            print(f"[CONFIG] Entorno forzado a LOCAL: {gateway_url}")
        elif args.env == "cloud":
            gateway_url = "https://ecostream-gateway.onrender.com"
            if not engine_endpoint:
                engine_endpoint = "ecostream-engine.onrender.com:443"
            print(f"[CONFIG] Entorno forzado a CLOUD (Render): {gateway_url}")
        elif discover_servers:
            print("[DISCOVERY] Buscando servidor local vía mDNS (_ecostream._tcp.local.) o HTTP...")
            gw, eng, mode = discover_servers(prefer_local=True)
            gateway_url = gw
            if not engine_endpoint:
                engine_endpoint = eng
            print(f"[DISCOVERY] Servidor resuelto [{mode}]: Gateway={gateway_url}, Engine={engine_endpoint}")
        else:
            gateway_url = "https://ecostream-gateway.onrender.com"
            if not engine_endpoint:
                engine_endpoint = "ecostream-engine.onrender.com:443"

    bot = EcoBot(
        gateway_url=gateway_url,
        engine_endpoint=engine_endpoint,
        username=args.username,
        room_code=args.room,
        role=args.role,
        duration=args.duration
    )
    success = bot.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
