#!/usr/bin/env python3
"""
EcoStream 3R - AquaGuardians: Cliente de Videojuego en Tiempo Real (Pygame-CE + gRPC)
Edición Gráfica Mejorada:
- Ondas de agua sinusoidales multi-capa en embalse central.
- Sistema de partículas para fugas a presión (agua) y reparación (chispas).
- Notificaciones y textos flotantes de puntaje animadas (+150 PTS).
- Barra HUD moderna con indicadores de estado, pureza y telemetría RTT.
- Modo Jugador Humano y Modo Bot Autónomo (--bot).
"""

import sys
import time
import math
import heapq
import random
import json
import argparse
import threading
import logging
import urllib.request
import urllib.error
from typing import List, Tuple, Optional, Set
from pathlib import Path

# Configurar logging explícito de ciclo de vida
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("EcoStreamClient")

# Configurar path de stubs proto
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "client-python" / "proto"))
sys.path.insert(0, str(ROOT_DIR / "client-python"))

try:
    from discovery import discover_servers
except ImportError:
    discover_servers = None

import grpc
import pygame
from ecostream.v1 import common_pb2
from ecostream.v1 import gameplay_pb2
from ecostream.v1 import gameplay_pb2_grpc


def authenticate_and_join_room(gateway_url: str, username: str, room_code: str = "") -> Tuple[str, str, str, str, str]:
    """
    Autenticación rápida sin contraseña en el Gateway REST y obtención de RoomTicket HMAC.
    Retorna: (jwt_token, user_id, room_id, room_ticket, simulation_endpoint)
    """
    gateway_url = gateway_url.rstrip("/")
    # 1. Login por nickname sin contraseña
    login_url = f"{gateway_url}/api/v1/auth/login"
    login_payload = json.dumps({"username": username}).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    req = urllib.request.Request(login_url, data=login_payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15.0) as resp:
        data = json.loads(resp.read().decode())
        token = data.get("token") or data.get("access_token", "")
        user = data.get("user", {})
        user_id = user.get("user_id", f"usr_{username}")

    auth_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # 2. Join o Create Room
    if room_code:
        join_url = f"{gateway_url}/api/v1/rooms/join"
        join_payload = json.dumps({"room_code": room_code, "role": 1}).encode("utf-8")
        req = urllib.request.Request(join_url, data=join_payload, headers=auth_headers, method="POST")
    else:
        join_url = f"{gateway_url}/api/v1/rooms/create"
        join_payload = json.dumps({
            "room_name": f"Partida_{username}",
            "role": 1,
            "max_players": 4,
            "difficulty": 1
        }).encode("utf-8")
        req = urllib.request.Request(join_url, data=join_payload, headers=auth_headers, method="POST")

    with urllib.request.urlopen(req, timeout=15.0) as resp:
        room_data = json.loads(resp.read().decode())
        room = room_data.get("room", {})
        room_id = room.get("id") or room.get("room_id", "rm_demo_01")
        room_ticket = room_data.get("room_ticket", "")
        simulation_endpoint = room.get("simulation_endpoint", "localhost:50052")

    return token, user_id, room_id, room_ticket, simulation_endpoint

# Clases fallback para renderizado continuo y modo desconectado
class LocalPipe:
    def __init__(self, pipe_id: int, is_leaking: bool = False, pressure: float = 3.2):
        self.pipe_id = pipe_id
        self.is_leaking = is_leaking
        self.pressure = pressure

class LocalValve:
    def __init__(self, valve_id: int, is_open: bool = True):
        self.valve_id = valve_id
        self.is_open = is_open

class LocalPlant:
    def __init__(self, plant_id: int, purity_level: float = 95.0):
        self.plant_id = plant_id
        self.purity_level = purity_level

# Dimensiones de la ventana
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 680
FPS = 60

# Paleta de Colores Cyber-Eco
COLOR_BG = (10, 14, 26)
COLOR_PANEL_BG = (15, 23, 42)
COLOR_PANEL_BORDER = (56, 189, 248)
COLOR_RESERVOIR = (14, 165, 233)
COLOR_RESERVOIR_LIGHT = (56, 189, 248)
COLOR_RESERVOIR_BG = (12, 45, 75)
COLOR_PURITY = (52, 211, 153)
COLOR_PIPE_OK = (71, 85, 105)
COLOR_PIPE_LEAK = (239, 68, 68)
COLOR_VALVE = (245, 158, 11)
COLOR_PLANT = (168, 85, 247)
COLOR_PLAYER = (14, 165, 233)
COLOR_BOT = (236, 72, 153)
COLOR_TEXT = (248, 250, 252)
COLOR_TEXT_MUTED = (148, 163, 184)
COLOR_PING_GOOD = (34, 197, 94)
COLOR_PING_WARN = (234, 179, 8)
COLOR_PING_BAD = (239, 68, 68)

class Particle:
    def __init__(self, x, y, vx, vy, color, size, life):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.life = life
        self.max_life = life

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 0.02
        return self.life > 0

class FloatingText:
    def __init__(self, text, x, y, color):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.alpha = 255
        self.life = 1.0

    def update(self):
        self.y -= 1.2
        self.life -= 0.02
        self.alpha = max(0, int(255 * self.life))
        return self.life > 0

class EcoStreamGameClient:
    def __init__(self, host="localhost:50052", hosts=None, room_id="rm_demo_01", player_id="usr_victor", room_ticket="", is_bot=False):
        raw_hosts = hosts if hosts else host
        self.host_list = [h.strip() for h in raw_hosts.split(",") if h.strip()]
        self.host = self.host_list[0] if self.host_list else "localhost:50052"
        self.current_host_idx = 0
        self.room_id = room_id
        self.player_id = player_id
        self.room_ticket = room_ticket
        self.is_bot = is_bot
        self.running = True

        # Estado del juego sincronizado desde Rust / Mock (20Hz)
        self.tick = 0
        self.reservoir_pct = 100.0
        self.purity_pct = 96.0
        self.liters_saved = 0.0
        self.liters_reused = 0.0
        self.liters_recycled = 0.0
        self.team_score = 0
        self.remaining_seconds = 180
        self.rtt_ms = 0
        self.reconnect_ticket = ""
        self.is_connected = False

        # Entidades locales con valores iniciales por defecto (evita pantalla vacía)
        self.player_x = 380.0
        self.player_y = 320.0
        self.vx = 0.0
        self.vy = 0.0
        self.dash_cooldown = 0.0
        self.dash_timer = 0.0
        self.remote_players = []
        self.active_events = []
        self.pipes = [
            LocalPipe(pipe_id=1, is_leaking=False),
            LocalPipe(pipe_id=2, is_leaking=True),
            LocalPipe(pipe_id=3, is_leaking=False),
        ]
        self.valves = [LocalValve(valve_id=1)]
        self.plants = [LocalPlant(plant_id=1)]

        # Cola de acciones hacia el servidor
        self.action_queue = []
        self.lock = threading.Lock()

        # Efectos visuales
        self.particles = []
        self.floating_texts = []

        # Estado de flujo del juego (INTRO -> PLAYING -> GAMEOVER / VICTORY)
        self.game_state = "PLAYING" if self.is_bot else "INTRO"
        self.game_over_reason = ""
        self.natural_leak_timer = 12.0

        logger.info(f"Iniciando EcoStreamGameClient en sala '{self.room_id}' (Jugador: {self.player_id}, Bot: {self.is_bot})")
        logger.info(f"Nodos de backend configurados: {self.host_list}")

        # Iniciar hilo de comunicación gRPC
        self.grpc_thread = threading.Thread(target=self._run_grpc_stream, daemon=True)
        self.grpc_thread.start()

    def restart_game(self):
        """Reinicia la simulación comunal y restaura métricas iniciales"""
        self.reservoir_pct = 100.0
        self.purity_pct = 96.0
        self.team_score = 0
        self.liters_saved = 0.0
        self.liters_reused = 0.0
        self.liters_recycled = 0.0
        self.remaining_seconds = 180.0
        self.game_state = "PLAYING"
        self.game_over_reason = ""
        self.pipes = [
            LocalPipe(pipe_id=1, is_leaking=False),
            LocalPipe(pipe_id=2, is_leaking=True),
            LocalPipe(pipe_id=3, is_leaking=False),
        ]
        self.player_x = 380.0
        self.player_y = 320.0
        self.vx = 0.0
        self.vy = 0.0
        self.natural_leak_timer = 12.0
        self.floating_texts.clear()
        self.particles.clear()
        logger.info("Partida reiniciada correctamente.")

    def _run_grpc_stream(self):
        """Streaming bidireccional continuo con alta disponibilidad y failover automático (20 Hz)"""
        channel_options = [
            ('grpc.keepalive_time_ms', 1000),             # Enviar ping keepalive cada 1 segundo
            ('grpc.keepalive_timeout_ms', 1500),          # Timeout de 1.5s para detectar corte físico de cable
            ('grpc.http2.max_pings_without_data', 0),     # Pings continuos permitidos
            ('grpc.keepalive_permit_without_calls', 1),   # Mantener keepalive aún en reposo
            ('grpc.initial_reconnect_backoff_ms', 500),   # Reintento rápido a 500ms
            ('grpc.max_reconnect_backoff_ms', 2000),      # Backoff máximo de 2s
        ]

        while self.running:
            raw_host = self.host_list[self.current_host_idx % len(self.host_list)]
            current_host = raw_host.replace("http://", "").replace("https://", "").strip()
            channel = None
            try:
                use_tls = ":443" in current_host
                logger.info(f"[gRPC Red] Conectando a nodo autoritativo: {current_host} (TLS={use_tls})...")
                if use_tls:
                    creds = grpc.ssl_channel_credentials()
                    channel = grpc.secure_channel(current_host, creds, options=channel_options)
                else:
                    channel = grpc.insecure_channel(current_host, options=channel_options)
                stub = gameplay_pb2_grpc.GameSimulationServiceStub(channel)

                def request_generator():
                    t_now = int(time.time() * 1000)
                    yield gameplay_pb2.ClientStreamMessage(
                        room_id=self.room_id,
                        player_id=self.player_id,
                        client_tick=1,
                        room_ticket=self.room_ticket,
                        ping=common_pb2.PingMessage(client_timestamp_ms=t_now, sequence_id=1)
                    )

                    client_tick = 1
                    while self.running:
                        time.sleep(0.05)  # 20 Hz
                        client_tick += 1
                        t_now = int(time.time() * 1000)

                        action = None
                        with self.lock:
                            if self.action_queue:
                                action = self.action_queue.pop(0)

                        # Enviar acción del jugador O sincronizar posición (MoveAction)
                        # Nota: action y ping están en 'oneof payload', no deben enviarse juntos
                        if action is not None:
                            msg = gameplay_pb2.ClientStreamMessage(
                                room_id=self.room_id,
                                player_id=self.player_id,
                                client_tick=client_tick,
                                room_ticket=self.room_ticket,
                                action=action
                            )
                        else:
                            msg = gameplay_pb2.ClientStreamMessage(
                                room_id=self.room_id,
                                player_id=self.player_id,
                                client_tick=client_tick,
                                room_ticket=self.room_ticket,
                                action=gameplay_pb2.PlayerAction(
                                    action_id=client_tick,
                                    move=gameplay_pb2.MoveAction(
                                        target_position=common_pb2.Vector2D(x=float(self.player_x), y=float(self.player_y)),
                                        velocity=common_pb2.Vector2D(x=float(self.vx), y=float(self.vy))
                                    )
                                )
                            )
                        yield msg

                responses = stub.StreamGame(request_generator())
                first_packet = True
                for resp in responses:
                    if not self.running:
                        break
                    if first_packet:
                        self.is_connected = True
                        first_packet = False
                        logger.info(f"✅ [gRPC Red] Sesión bidireccional activa con nodo autoritativo {current_host}")

                    if resp.HasField("initial_snapshot"):
                        self.reconnect_ticket = resp.initial_snapshot.reconnect_ticket
                        logger.info(f"[gRPC Sync] Snapshot inicial recibido. Ticket de reconexión: {self.reconnect_ticket}")

                    if resp.HasField("world_state"):
                        ws = resp.world_state
                        self.tick = ws.tick
                        if ws.water_metrics:
                            self.reservoir_pct = ws.water_metrics.reservoir_level_pct
                            self.purity_pct = ws.water_metrics.water_purity_pct
                            self.liters_saved = ws.water_metrics.total_liters_saved
                            self.liters_reused = ws.water_metrics.total_liters_reused
                            self.liters_recycled = ws.water_metrics.total_liters_recycled
                        self.team_score = ws.team_score
                        self.remaining_seconds = ws.remaining_seconds
                        if ws.pipes:
                            self.pipes = ws.pipes
                        if ws.valves:
                            self.valves = ws.valves
                        if ws.plants:
                            self.plants = ws.plants
                        if ws.players:
                            self.remote_players = [p for p in ws.players if p.player_id != self.player_id]
                        if ws.active_events:
                            self.active_events = list(ws.active_events)
                        else:
                            self.active_events = []

                    if resp.HasField("pong"):
                        self.rtt_ms = int(time.time() * 1000) - resp.pong.echo_client_timestamp_ms

            except grpc.RpcError as e:
                is_clean_eof = not self.running or "END_STREAM" in str(e)
                if not is_clean_eof:
                    if self.is_connected:
                        logger.warning(f"⚠️ [FALLO DE NODO / CORTE FÍSICO] Servidor {current_host} caído o inalcanzable: {e}")
                    self.is_connected = False
                    self.current_host_idx += 1
                    next_host = self.host_list[self.current_host_idx % len(self.host_list)]
                    logger.info(f"⚡ [FAILOVER AUTOMÁTICO] Conmutando a réplica secundaria: {next_host}...")
                    time.sleep(1.0)
            except Exception as ex:
                if not self.running:
                    break
                if self.is_connected:
                    logger.warning(f"⚠️ [FALLO DE NODO / CORTE FÍSICO] Servidor {current_host} caído o inalcanzable: {ex}")
                self.is_connected = False
                self.current_host_idx += 1
                next_host = self.host_list[self.current_host_idx % len(self.host_list)]
                logger.info(f"⚡ [FAILOVER AUTOMÁTICO] Conmutando a réplica secundaria: {next_host}...")
                time.sleep(1.0)
            finally:
                if channel:
                    try:
                        channel.close()
                    except Exception:
                        pass

    def queue_action(self, action):
        with self.lock:
            self.action_queue.append(action)

    def spawn_sparks(self, x, y):
        for _ in range(16):
            vx = (random.random() - 0.5) * 6
            vy = (random.random() - 0.8) * 6
            c = random.choice([(250, 204, 21), (56, 189, 248), (255, 255, 255)])
            self.particles.append(Particle(x, y, vx, vy, c, random.randint(2, 4), 1.0))

    def _world_to_grid(self, x: float, y: float, cell_size: int = 30) -> Tuple[int, int]:
        return int(x // cell_size), int(y // cell_size)

    def _grid_to_world(self, gx: int, gy: int, cell_size: int = 30) -> Tuple[float, float]:
        return float(gx * cell_size + cell_size / 2), float(gy * cell_size + cell_size / 2)

    def _get_obstacles(self, cell_size: int = 30) -> Set[Tuple[int, int]]:
        """Obstáculos estáticos del mapa: embalse central y bordes"""
        obstacles = set()
        # Embalse izquierdo (X: 30 a 270, Y: 110 a 640)
        min_gx, min_gy = self._world_to_grid(30, 110, cell_size)
        max_gx, max_gy = self._world_to_grid(270, 640, cell_size)
        for gx in range(min_gx, max_gx + 1):
            for gy in range(min_gy, max_gy + 1):
                obstacles.add((gx, gy))

        # Bordes de la ventana
        max_w_g = WINDOW_WIDTH // cell_size
        max_h_g = WINDOW_HEIGHT // cell_size
        for gx in range(max_w_g):
            obstacles.add((gx, 0))
            obstacles.add((gx, max_h_g - 1))
        for gy in range(max_h_g):
            obstacles.add((0, gy))
            obstacles.add((max_w_g - 1, gy))

        return obstacles

    def astar_pathfind(self, start_pos: Tuple[float, float], target_pos: Tuple[float, float]) -> List[Tuple[float, float]]:
        """
        Algoritmo A* (A-Star) en cuadrícula 2D con distancia euclidiana como heurística.
        Calcula la ruta más corta evitando obstáculos del mapa de juego.
        """
        cell_size = 25
        start_node = self._world_to_grid(start_pos[0], start_pos[1], cell_size)
        target_node = self._world_to_grid(target_pos[0], target_pos[1], cell_size)

        if start_node == target_node:
            return [target_pos]

        obstacles = self._get_obstacles(cell_size)

        # Priority Queue: (f_score, g_score, current_node)
        open_set = []
        heapq.heappush(open_set, (0.0, 0.0, start_node))
        came_from = {}
        g_scores = {start_node: 0.0}

        def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
            # Distancia euclidiana
            return math.hypot(a[0] - b[0], a[1] - b[1])

        # Movimientos ortogonales y diagonales (8 direcciones)
        directions = [
            (0, 1, 1.0), (1, 0, 1.0), (0, -1, 1.0), (-1, 0, 1.0),
            (1, 1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (-1, -1, 1.414)
        ]

        max_iterations = 800
        iterations = 0

        while open_set and iterations < max_iterations:
            iterations += 1
            _, current_g, current = heapq.heappop(open_set)

            if current == target_node:
                # Reconstruir camino
                path = []
                curr = current
                while curr in came_from:
                    path.append(self._grid_to_world(curr[0], curr[1], cell_size))
                    curr = came_from[curr]
                path.reverse()
                path.append(target_pos)
                return path

            for dx, dy, cost in directions:
                neighbor = (current[0] + dx, current[1] + dy)
                if neighbor in obstacles and neighbor != target_node:
                    continue

                tentative_g = current_g + cost
                if tentative_g < g_scores.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_scores[neighbor] = tentative_g
                    f_score = tentative_g + heuristic(neighbor, target_node)
                    heapq.heappush(open_set, (f_score, tentative_g, neighbor))

        # Fallback de línea recta si no hay camino en la cuadrícula
        return [target_pos]

    def bot_ai_tick(self):
        """
        Lógica de IA del Bot con A* (Pathfinding Autónomo):
        1. Detecta automáticamente la rotura/fuga más cercana.
        2. Calcula la ruta óptima evitando colisiones con A*.
        3. Camina hacia el punto y envía la acción RepairPipeAction.
        4. Si no hay fugas, asiste en Reusar (válvulas) y Reciclar (planta).
        """
        leaking_pipes = [p for p in self.pipes if p.is_leaking]

        if leaking_pipes:
            # Detectar la fuga MÁS CERCANA al bot
            def pipe_distance(p):
                target_x = 420.0
                target_y = 180.0 + (p.pipe_id - 1) * 60.0
                return math.hypot(target_x - self.player_x, target_y - self.player_y)

            closest_pipe = min(leaking_pipes, key=pipe_distance)
            target_x = 420.0
            target_y = 180.0 + (closest_pipe.pipe_id - 1) * 60.0

            dist_to_target = math.hypot(target_x - self.player_x, target_y - self.player_y)

            # Si está fuera del rango de reparación, navegar usando A*
            if dist_to_target > 28.0:
                # Si no hay ruta calculada o cambió de objetivo, recalcular A*
                if not getattr(self, "bot_path", None) or getattr(self, "bot_target_pipe", None) != closest_pipe.pipe_id:
                    self.bot_path = self.astar_pathfind((self.player_x, self.player_y), (target_x, target_y))
                    self.bot_target_pipe = closest_pipe.pipe_id

                # Avanzar hacia el siguiente waypoint del camino A*
                if self.bot_path:
                    next_wp = self.bot_path[0]
                    wp_dx = next_wp[0] - self.player_x
                    wp_dy = next_wp[1] - self.player_y
                    wp_dist = math.hypot(wp_dx, wp_dy)

                    if wp_dist < 10.0:
                        self.bot_path.pop(0)
                    else:
                        step = min(5.0, wp_dist)
                        self.player_x += (wp_dx / wp_dist) * step
                        self.player_y += (wp_dy / wp_dist) * step
            else:
                # Rango alcanzado: Ejecutar reparación autoritativa
                self.bot_path = []
                self.spawn_sparks(self.player_x, self.player_y)
                self.queue_action(gameplay_pb2.PlayerAction(
                    action_id=int(time.time() * 1000),
                    repair_pipe=gameplay_pb2.RepairPipeAction(
                        pipe_id=closest_pipe.pipe_id,
                        repair_progress_delta=50.0
                    )
                ))
                self.floating_texts.append(FloatingText(
                    f"+150 PTS [A* Fuga #{closest_pipe.pipe_id} Sellada]",
                    self.player_x - 50, self.player_y - 25, (56, 189, 248)
                ))
            return

        # Si no hay fugas, limpiar ruta y patrullar tareas secundarias
        self.bot_path = []
        self.bot_target_pipe = None

        # Reusar aguas residuales a huertos
        if self.tick % 50 == 0 and self.valves:
            self.queue_action(gameplay_pb2.PlayerAction(
                action_id=int(time.time() * 1000),
                divert_valve=gameplay_pb2.DivertValveAction(valve_id=1, destination=gameplay_pb2.DESTINATION_IRRIGATION)
            ))
            self.floating_texts.append(FloatingText("+60 PTS [A* Riego Huerto 🌱]", self.player_x - 30, self.player_y - 20, (52, 211, 153)))
        # Reciclar en planta biológica
        elif self.tick % 70 == 0 and self.plants:
            self.queue_action(gameplay_pb2.PlayerAction(
                action_id=int(time.time() * 1000),
                operate_recycle=gameplay_pb2.OperateRecycleAction(plant_id=1, operation=gameplay_pb2.OperateRecycleAction.RECYCLE_OP_LOAD_FILTER)
            ))
    def run_headless(self, duration_sec: Optional[float] = None):
        """
        Ejecuta el loop de juego en modo headless (sin interfaz gráfica) a 20 Hz.
        Ideal para bots individuales y pruebas de rendimiento en servidores sin GUI.
        """
        print(f"[BOT HEADLESS] Bot '{self.player_id}' iniciado en sala '{self.room_id}' hacia {self.host}")
        start_time = time.time()
        tick_count = 0
        try:
            while True:
                time.sleep(0.05)  # 20 Hz (50 ms por tick)
                tick_count += 1
                if self.is_bot:
                    self.bot_ai_tick()
                if tick_count % 40 == 0:  # Cada 2 segundos
                    status = "ONLINE 20Hz" if self.is_connected else "RECONECTANDO"
                    print(f"[{self.player_id}] Tick #{self.tick} | Estado: {status} | Latencia: {self.rtt_ms}ms | Score: {self.team_score} | Ahorro: {self.liters_saved:.1f} L")
                if duration_sec and (time.time() - start_time) >= duration_sec:
                    print(f"[BOT HEADLESS] Duración de {duration_sec}s completada.")
                    break
        except KeyboardInterrupt:
            print(f"\n[BOT HEADLESS] Bot '{self.player_id}' detenido por el usuario.")
        finally:
            self.running = False

    def run(self):
        pygame.init()
        pygame.font.init()
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        mode_title = "MODO BOT AUTOMÁTICO" if self.is_bot else "MODO JUGADOR AQUAGUARDIAN"
        pygame.display.set_caption(f"EcoStream 3R - AquaGuardians [{mode_title}]")
        clock = pygame.time.Clock()

        font_title = pygame.font.SysFont("Segoe UI", 22, bold=True)
        font_large = pygame.font.SysFont("Segoe UI", 18, bold=True)
        font_med = pygame.font.SysFont("Segoe UI", 13, bold=True)
        font_small = pygame.font.SysFont("Segoe UI", 11)
        font_mono = pygame.font.SysFont("Consolas", 12, bold=True)

        # Carga directa de texturas pixel art limpias con transparencia alfa
        sprites = {}
        sprites_dir = ROOT_DIR / "client-python" / "assets" / "sprites"
        if sprites_dir.exists():
            for p in sprites_dir.glob("*.png"):
                try:
                    sprites[p.stem] = pygame.image.load(str(p)).convert_alpha()
                except Exception:
                    pass
            logger.info(f"🎨 [Sprites Pygame] {len(sprites)} texturas individuales cargadas con transparencia.")
        else:
            logger.warning("⚠️ [Sprites Pygame] Carpeta de sprites no encontrada. Usando fallback procedural.")

        running = True
        wave_time = 0.0

        while running:
            dt = clock.tick(FPS) / 1000.0
            wave_time += dt * 3.5

            # Eventos de entrada
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

                    # Si estamos en la pantalla de INTRODUCCIÓN
                    if self.game_state == "INTRO":
                        if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                            self.game_state = "PLAYING"
                            logger.info("Partida iniciada desde pantalla de introducción.")
                        continue

                    # Si estamos en pantalla de DERROTA o VICTORIA
                    if self.game_state in ("GAMEOVER", "VICTORY"):
                        if event.key in (pygame.K_r, pygame.K_SPACE, pygame.K_RETURN):
                            self.restart_game()
                        continue

                    # Acciones del jugador en modo PLAYING
                    if (event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT) and not self.is_bot:
                        # Activar Dash sónico
                        if self.dash_cooldown <= 0:
                            self.dash_timer = 0.22
                            self.dash_cooldown = 0.95
                            dash_speed = 680.0
                            mag = math.hypot(self.vx, self.vy)
                            if mag > 10:
                                self.vx = (self.vx / mag) * dash_speed
                                self.vy = (self.vy / mag) * dash_speed
                            else:
                                self.vx = dash_speed
                            for _ in range(16):
                                self.particles.append(Particle(self.player_x, self.player_y, (random.random()-0.5)*5, (random.random()-0.5)*5, (56, 189, 248), 3, 0.5))
                            self.floating_texts.append(FloatingText("DASH!", self.player_x - 15, self.player_y - 25, (56, 189, 248)))
                    elif not self.is_bot and event.key == pygame.K_SPACE:
                        # 1. Reducir: requiere proximidad física con las tuberías (X: ~440, Y: 140-300)
                        dist_to_pipes = math.hypot(self.player_x - 440, self.player_y - 215)
                        if dist_to_pipes < 140:
                            repaired = False
                            for p in self.pipes:
                                if p.is_leaking:
                                    p.is_leaking = False
                                    repaired = True
                                    self.spawn_sparks(self.player_x, self.player_y)
                                    self.team_score += 150
                                    self.liters_saved += 120.0
                                    self.queue_action(gameplay_pb2.PlayerAction(
                                        action_id=int(time.time()*1000),
                                        repair_pipe=gameplay_pb2.RepairPipeAction(pipe_id=p.pipe_id, repair_progress_delta=50.0)
                                    ))
                                    self.floating_texts.append(FloatingText("+150 PTS (Fuga Reparada!)", self.player_x - 40, self.player_y - 20, (56, 189, 248)))
                                    logger.info(f"[Acción 3R - Reducir] Tubería #{p.pipe_id} reparada con éxito. +150 PTS")
                                    break
                            if not repaired:
                                self.floating_texts.append(FloatingText("Tuberias Seguras (Presion Normal)", self.player_x - 60, self.player_y - 20, (148, 163, 184)))
                        else:
                            self.floating_texts.append(FloatingText("Acercate a la Zona de Tuberias", self.player_x - 60, self.player_y - 20, (239, 68, 68)))
                    elif not self.is_bot and event.key == pygame.K_r:
                        # 2. Reusar: requiere proximidad física con el Huerto / Válvula (X: ~440, Y: 480)
                        dist_to_garden = math.hypot(self.player_x - 440, self.player_y - 480)
                        if dist_to_garden < 150:
                            self.team_score += 80
                            self.liters_reused += 85.0
                            self.queue_action(gameplay_pb2.PlayerAction(
                                action_id=int(time.time()*1000),
                                divert_valve=gameplay_pb2.DivertValveAction(valve_id=1, destination=gameplay_pb2.DESTINATION_IRRIGATION)
                            ))
                            self.floating_texts.append(FloatingText("+80 PTS (Riego de Huerto)", self.player_x - 40, self.player_y - 20, (52, 211, 153)))
                            logger.info("[Acción 3R - Reusar] Válvula desviada a huerto comunitario. +80 PTS")
                        else:
                            self.floating_texts.append(FloatingText("Acercate al Huerto Comunitario", self.player_x - 60, self.player_y - 20, (239, 68, 68)))
                    elif not self.is_bot and event.key == pygame.K_f:
                        # 3. Reciclar: requiere proximidad física con la Planta de Tratamiento UV (X: ~800, Y: 380)
                        dist_to_plant = math.hypot(self.player_x - 800, self.player_y - 380)
                        if dist_to_plant < 170:
                            self.team_score += 120
                            self.liters_recycled += 60.0
                            self.purity_pct = min(100.0, self.purity_pct + 1.5)
                            self.queue_action(gameplay_pb2.PlayerAction(
                                action_id=int(time.time()*1000),
                                operate_recycle=gameplay_pb2.OperateRecycleAction(plant_id=1, operation=gameplay_pb2.OperateRecycleAction.RECYCLE_OP_LOAD_FILTER)
                            ))
                            self.floating_texts.append(FloatingText("+120 PTS (Filtro UV Activado)", self.player_x - 40, self.player_y - 20, (192, 132, 252)))
                            logger.info("[Acción 3R - Reciclar] Filtro UV activado. Pureza incrementada. +120 PTS")
                        else:
                            self.floating_texts.append(FloatingText("Acercate a la Planta UV", self.player_x - 60, self.player_y - 20, (239, 68, 68)))

            # Lógica y actualización en modo PLAYING
            if self.game_state == "PLAYING":
                # Movimiento Jugador con física suave y normalización diagonal
                if not self.is_bot:
                    keys = pygame.key.get_pressed()
                    in_x, in_y = 0.0, 0.0
                    if keys[pygame.K_w] or keys[pygame.K_UP]: in_y -= 1.0
                    if keys[pygame.K_s] or keys[pygame.K_DOWN]: in_y += 1.0
                    if keys[pygame.K_a] or keys[pygame.K_LEFT]: in_x -= 1.0
                    if keys[pygame.K_d] or keys[pygame.K_RIGHT]: in_x += 1.0

                    if in_x != 0.0 or in_y != 0.0:
                        mag = math.hypot(in_x, in_y)
                        in_x /= mag
                        in_y /= mag

                    # Actualizar enfriamiento de Dash
                    if self.dash_cooldown > 0:
                        self.dash_cooldown -= dt

                    if self.dash_timer > 0:
                        self.dash_timer -= dt
                    else:
                        accel = 1650.0
                        self.vx += in_x * accel * dt
                        self.vy += in_y * accel * dt
                        friction = math.exp(-7.5 * dt)
                        self.vx *= friction
                        self.vy *= friction

                    self.player_x = max(45.0, min(WINDOW_WIDTH - 45.0, self.player_x + self.vx * dt))
                    self.player_y = max(115.0, min(WINDOW_HEIGHT - 45.0, self.player_y + self.vy * dt))
                else:
                    self.bot_ai_tick()

                # Fuga natural periódica (la rotura ocurre por tiempo/presión, NO porque el usuario presione Espacio)
                self.natural_leak_timer -= dt
                if self.natural_leak_timer <= 0:
                    self.natural_leak_timer = random.uniform(10.0, 16.0)
                    ok_pipes = [p for p in self.pipes if not p.is_leaking]
                    if ok_pipes:
                        target_p = random.choice(ok_pipes)
                        target_p.is_leaking = True
                        self.floating_texts.append(FloatingText(f"[!] Fuga en Tuberia #{target_p.pipe_id}", 440, 180 + (target_p.pipe_id - 1) * 60, (239, 68, 68)))
                        logger.info(f"Presión comunal generó fuga automática en tubería #{target_p.pipe_id}")

                # Consumo y drenaje de agua según fugas
                has_leak = any(p.is_leaking for p in self.pipes)
                leak_count = sum(1 for p in self.pipes if p.is_leaking)
                if has_leak:
                    # Las fugas drenan el embalse y degradan la pureza
                    self.reservoir_pct = max(0.0, self.reservoir_pct - dt * (0.35 * leak_count))
                    self.purity_pct = max(0.0, self.purity_pct - dt * (0.07 * leak_count))
                else:
                    # Drenaje mínimo de consumo comunal urbano
                    self.reservoir_pct = max(0.0, self.reservoir_pct - dt * 0.02)

                # Tiempo restante de partida
                self.remaining_seconds = max(0.0, self.remaining_seconds - dt)

                # =========================================================
                # CONDICIONES DE DERROTA (GAME OVER) Y VICTORIA
                # =========================================================
                if self.reservoir_pct <= 0.0:
                    self.game_state = "GAMEOVER"
                    self.game_over_reason = "SEQUIA TOTAL: El embalse se ha vaciado por completo.\nLas fugas sin reparar agotaron el suministro vital."
                    logger.warning("DERROTA: El embalse llegó a 0%.")
                elif self.purity_pct < 40.0:
                    self.game_state = "GAMEOVER"
                    self.game_over_reason = f"CONTAMINACION CRITICA: La pureza cayo a {self.purity_pct:.1f}%.\nEl agua ya no es potable y amenaza la salud comunal."
                    logger.warning("DERROTA: Pureza crítica inferior al 40%.")
                elif self.remaining_seconds <= 0.0:
                    self.game_state = "VICTORY"
                    logger.info("VICTORIA: Tiempo completado con métricas seguras.")

            # Partículas continuas de fugas activas
            for p in self.pipes:
                if p.is_leaking and random.random() < 0.4:
                    px = 440.0
                    py = 180.0 + (p.pipe_id - 1) * 60.0
                    self.particles.append(Particle(
                        px + (random.random() - 0.5) * 20,
                        py,
                        (random.random() - 0.5) * 3,
                        -random.random() * 4 - 1,
                        (56, 189, 248),
                        random.randint(2, 4),
                        0.8
                    ))

            # -------------------------------------------------------------
            # RENDERIZADO DEL MUNDO
            # -------------------------------------------------------------
            screen.fill(COLOR_BG)

            # A. EMBALSE PRINCIPAL
            res_rect = pygame.Rect(30, 110, 240, 530)
            pygame.draw.rect(screen, COLOR_RESERVOIR_BG, res_rect, border_radius=14)
            
            fill_h = int(500 * (max(0.0, self.reservoir_pct) / 100.0))
            if fill_h > 0:
                water_rect = pygame.Rect(30, 110 + (530 - fill_h), 240, fill_h)
                pygame.draw.rect(screen, COLOR_RESERVOIR, water_rect, border_radius=14)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, res_rect, 2, border_radius=14)

            # Ondas decorativas si hay agua
            if fill_h > 10:
                for ox in range(35, 265, 8):
                    oy = 110 + (530 - fill_h) + int(math.sin(ox * 0.08 + wave_time) * 3.0)
                    pygame.draw.circle(screen, (255, 255, 255), (ox, oy), 2)

            # Presa de concreto Pixel Art coronando el embalse
            if "dam" in sprites:
                dam_surf = pygame.transform.smoothscale(sprites["dam"], (236, 118))
                screen.blit(dam_surf, (32, 112))

            if "icon_droplet" in sprites:
                icon_d = pygame.transform.scale(sprites["icon_droplet"], (20, 20))
                screen.blit(icon_d, (42, 122))
                screen.blit(font_med.render(f"EMBALSE: {self.reservoir_pct:.1f}%", True, COLOR_TEXT), (68, 123))
            else:
                screen.blit(font_med.render(f"EMBALSE: {self.reservoir_pct:.1f}%", True, COLOR_TEXT), (45, 125))

            # B. ZONA 1: REDUCIR
            z1 = pygame.Rect(300, 110, 290, 250)
            pygame.draw.rect(screen, (22, 32, 54), z1, border_radius=12)
            pygame.draw.rect(screen, (71, 85, 105), z1, 2, border_radius=12)

            if "icon_wrench" in sprites:
                icon_w = pygame.transform.scale(sprites["icon_wrench"], (20, 20))
                screen.blit(icon_w, (315, 120))
                screen.blit(font_med.render("1. REDUCIR (Fugas Comunales)", True, (248, 113, 113)), (340, 122))
            else:
                screen.blit(font_med.render("1. REDUCIR (Fugas Comunales)", True, (248, 113, 113)), (315, 122))

            for i, p in enumerate(self.pipes):
                py_y = 160 + i * 60
                drawn_pipe = False
                if p.is_leaking and "pipe_leaking" in sprites:
                    pipe_s = pygame.transform.scale(sprites["pipe_leaking"], (230, 48))
                    screen.blit(pipe_s, (315, py_y - 6))
                    drawn_pipe = True
                elif not p.is_leaking and "pipe_straight" in sprites:
                    pipe_s = pygame.transform.scale(sprites["pipe_straight"], (230, 36))
                    screen.blit(pipe_s, (315, py_y))
                    drawn_pipe = True

                if "valve_red" in sprites:
                    valve_s = pygame.transform.scale(sprites["valve_red"], (26, 32))
                    screen.blit(valve_s, (550, py_y + 2))

                if not drawn_pipe:
                    p_color = COLOR_PIPE_LEAK if p.is_leaking else COLOR_PIPE_OK
                    pygame.draw.rect(screen, p_color, (315, py_y, 260, 36), border_radius=6)

                txt = f"Tuberia #{p.pipe_id}: {'[!] FUGA CRITICA' if p.is_leaking else '(OK) Presion Estable'}"
                screen.blit(font_small.render(txt, True, (0, 0, 0)), (326, py_y + 9))
                screen.blit(font_small.render(txt, True, (255, 255, 255) if not p.is_leaking else (254, 202, 202)), (325, py_y + 8))

            # C. ZONA 2: REUSAR
            z2 = pygame.Rect(300, 380, 290, 260)
            pygame.draw.rect(screen, (20, 83, 45), z2, border_radius=12)
            pygame.draw.rect(screen, (34, 197, 94), z2, 2, border_radius=12)

            if "icon_shovel" in sprites:
                icon_s = pygame.transform.scale(sprites["icon_shovel"], (20, 20))
                screen.blit(icon_s, (315, 393))
                screen.blit(font_med.render("2. REUSAR (Huertos Comunitarios)", True, (134, 239, 172)), (340, 395))
            else:
                screen.blit(font_med.render("2. REUSAR (Huertos Comunitarios)", True, (134, 239, 172)), (315, 395))

            screen.blit(font_small.render(f"Reuso acumulado: {self.liters_reused:.0f} L", True, (220, 252, 231)), (315, 425))
            screen.blit(font_small.render("Valvula canalizada a riego por goteo", True, COLOR_TEXT_MUTED), (315, 445))

            # Vegetación y árboles pixel art en el huerto (limpios sin fondos blancos)
            if "tree_oak" in sprites:
                screen.blit(pygame.transform.scale(sprites["tree_oak"], (60, 60)), (520, 388))
            if "tree_pine" in sprites:
                screen.blit(pygame.transform.scale(sprites["tree_pine"], (38, 56)), (480, 390))

            # Parcelas de tierra labrada con cultivos pixel art
            for idx_c, cx in enumerate(range(320, 560, 58)):
                pygame.draw.rect(screen, (69, 26, 3), (cx, 485, 48, 38), border_radius=4)
                pygame.draw.rect(screen, (120, 53, 15), (cx + 4, 492, 40, 4))
                pygame.draw.rect(screen, (120, 53, 15), (cx + 4, 506, 40, 4))
                if "bush" in sprites and idx_c % 2 == 0:
                    screen.blit(pygame.transform.scale(sprites["bush"], (32, 28)), (cx + 8, 488))
                elif "flowers" in sprites:
                    screen.blit(pygame.transform.scale(sprites["flowers"], (28, 24)), (cx + 10, 492))

            # D. ZONA 3: RECICLAR
            z3 = pygame.Rect(615, 110, 380, 530)
            pygame.draw.rect(screen, (46, 16, 77), z3, border_radius=12)
            pygame.draw.rect(screen, COLOR_PLANT, z3, 2, border_radius=12)

            if "icon_recycle" in sprites:
                icon_r = pygame.transform.scale(sprites["icon_recycle"], (20, 20))
                screen.blit(icon_r, (630, 123))
                screen.blit(font_med.render("3. RECICLAR (Planta Filtrado UV)", True, (216, 180, 254)), (655, 125))
            else:
                screen.blit(font_med.render("3. RECICLAR (Planta Filtrado UV)", True, (216, 180, 254)), (630, 125))

            # Complejo de Planta de Filtrado Industrial Pixel Art
            if "plant" in sprites:
                plant_surf = pygame.transform.smoothscale(sprites["plant"], (345, 195))
                screen.blit(plant_surf, (632, 148))

            screen.blit(font_med.render(f"Pureza Hidrica: {self.purity_pct:.1f}%", True, COLOR_PURITY), (630, 355))
            screen.blit(font_small.render(f"Agua Descontaminada: {self.liters_recycled:.0f} L", True, (243, 232, 255)), (630, 380))

            # Turbina/Reactor de Biofiltración y Rayos UV (Animado con brillo)
            center_x, center_y = 805, 480
            pygame.draw.circle(screen, (168, 85, 247), (center_x, center_y), 52, 3)
            pygame.draw.circle(screen, (216, 180, 254), (center_x, center_y), 22)
            pygame.draw.circle(screen, (255, 255, 255), (center_x, center_y), 12)
            for a in range(4):
                ang = wave_time * 1.5 + a * (math.pi / 2.0)
                fx = center_x + int(math.cos(ang) * 44)
                fy = center_y + int(math.sin(ang) * 44)
                pygame.draw.line(screen, (192, 132, 252), (center_x, center_y), (fx, fy), 4)
            tag_uv = font_small.render("Reactor UV & Carbon Activo", True, (216, 180, 254))
            screen.blit(tag_uv, (center_x - tag_uv.get_width() // 2, center_y + 60))

            # E. PARTÍCULAS
            self.particles = [p for p in self.particles if p.update()]
            for p in self.particles:
                pygame.draw.circle(screen, p.color, (int(p.x), int(p.y)), p.size)

            # Helper para renderizado del personaje AquaGuardian
            def draw_character(x, y, vx, vy, is_dashing, is_bot_char, label, is_self=False):
                # Sombra elíptica en el suelo
                shadow_surf = pygame.Surface((34, 12), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow_surf, (0, 0, 0, 110), (0, 0, 34, 12))
                screen.blit(shadow_surf, (int(x) - 17, int(y) + 16))

                # Halo luminoso
                halo_col = (251, 191, 36) if is_dashing else ((56, 189, 248) if is_self else (34, 197, 94))
                pygame.draw.circle(screen, halo_col, (int(x), int(y) + 2), 24, 2)

                char_drawn = False
                if sprites:
                    is_moving = math.hypot(vx, vy) > 10
                    flip_x = (vx < -5)
                    d_pipe_chk = math.hypot(x - 440, y - 215)
                    d_garden_chk = math.hypot(x - 440, y - 480)

                    char_sprite = sprites.get("worker_idle")
                    if is_dashing:
                        char_sprite = sprites.get("worker_welder", char_sprite)
                    elif d_pipe_chk < 140 and any(p.is_leaking for p in self.pipes):
                        frames = [sprites.get(f"worker_wrench{i}") for i in (0, 1) if sprites.get(f"worker_wrench{i}")]
                        if frames: char_sprite = frames[int(wave_time * 3) % len(frames)]
                    elif d_garden_chk < 150:
                        frames = [sprites.get(f"worker_shovel{i}") for i in (0, 1) if sprites.get(f"worker_shovel{i}")]
                        if frames: char_sprite = frames[int(wave_time * 2.5) % len(frames)]
                    elif is_moving:
                        frames = [sprites.get(f"worker_walk{i}") for i in (0, 1, 2) if sprites.get(f"worker_walk{i}")]
                        if frames: char_sprite = frames[int(wave_time * 4) % len(frames)]

                    if char_sprite:
                        worker_s = pygame.transform.scale(char_sprite, (36, 54))
                        if flip_x:
                            worker_s = pygame.transform.flip(worker_s, True, False)
                        screen.blit(worker_s, (int(x) - 18, int(y) - 28))
                        char_drawn = True

                if not char_drawn:
                    avatar_col = COLOR_BOT if is_bot_char else COLOR_PLAYER
                    pygame.draw.circle(screen, avatar_col, (int(x), int(y)), 18)
                    pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), 18, 2)

                # Etiqueta de identificación
                tag_surf = font_small.render(label, True, (255, 255, 255))
                screen.blit(tag_surf, (int(x) - tag_surf.get_width() // 2, int(y) - 44))

            # F. OTROS JUGADORES CONECTADOS
            for rp in self.remote_players:
                rx, ry = float(rp.position.x), float(rp.position.y)
                draw_character(rx, ry, 0.0, 0.0, False, False, rp.username, is_self=False)

            # G. AVATAR PROPIO
            self_lbl = "BOT" if self.is_bot else "TU"
            draw_character(self.player_x, self.player_y, self.vx, self.vy, self.dash_timer > 0, self.is_bot, self_lbl, is_self=True)

            # TOOLTIP FLOTANTE DE INTERACCIÓN SEGÚN PROXIMIDAD
            if not self.is_bot and self.game_state == "PLAYING":
                d_pipe = math.hypot(self.player_x - 440, self.player_y - 215)
                d_garden = math.hypot(self.player_x - 440, self.player_y - 480)
                d_plant = math.hypot(self.player_x - 800, self.player_y - 380)

                prompt = None
                if d_pipe < 140:
                    prompt = "[ESPACIO] Reparar Fuga"
                elif d_garden < 150:
                    prompt = "[R] Regar Huerto"
                elif d_plant < 170:
                    prompt = "[F] Filtrado UV"

                if prompt:
                    p_surf = font_small.render(prompt, True, (254, 240, 138))
                    screen.blit(p_surf, (int(self.player_x) - 40, int(self.player_y) - 34))

            # H. TEXTOS FLOTANTES
            self.floating_texts = [ft for ft in self.floating_texts if ft.update()]
            for ft in self.floating_texts:
                screen.blit(font_med.render(ft.text, True, ft.color), (int(ft.x), int(ft.y)))

            # I. EVENTOS CLIMÁTICOS / CAOS DINÁMICO
            if self.active_events and self.game_state == "PLAYING":
                ev = self.active_events[0]
                ev_rect = pygame.Rect(WINDOW_WIDTH // 2 - 210, 90, 420, 26)
                pygame.draw.rect(screen, (185, 28, 28), ev_rect, border_radius=6)
                pygame.draw.rect(screen, (254, 202, 202), ev_rect, 1, border_radius=6)
                screen.blit(font_small.render(f"[ALERTA] {ev.title} ({ev.remaining_seconds}s)", True, (255, 255, 255)), (WINDOW_WIDTH // 2 - 195, 95))

            # J. HUD SUPERIOR (SIN SOLAPAMIENTOS)
            pygame.draw.rect(screen, COLOR_PANEL_BG, (0, 0, WINDOW_WIDTH, 85))
            pygame.draw.line(screen, (51, 65, 85), (0, 85), (WINDOW_WIDTH, 85), 2)

            # Izquierda: Logo y controles
            screen.blit(font_title.render("EcoStream 3R", True, (56, 189, 248)), (25, 10))
            screen.blit(font_small.render(f"Lobby: [{self.room_id}] | Jugadores: {len(self.remote_players) + 1}", True, COLOR_TEXT_MUTED), (25, 38))
            screen.blit(font_small.render("Controles: [WASD] Mover | [SHIFT] Dash | [Espacio/R/F] Acciones 3R", True, (203, 213, 225)), (25, 58))

            # Centro: PUNTOS y métricas clave
            screen.blit(font_large.render(f"PUNTOS: {self.team_score}", True, (250, 204, 21)), (410, 14))
            tiempo_str = f"{int(self.remaining_seconds)}s"
            screen.blit(font_small.render(f"Ahorro: {self.liters_saved:.0f} L | Pureza: {self.purity_pct:.1f}% | Tiempo: {tiempo_str}", True, (52, 211, 153)), (410, 48))

            # Derecha: Widget Ping & Estado de Red
            active_node = self.host_list[self.current_host_idx % len(self.host_list)]
            if self.is_connected:
                ping_color = COLOR_PING_GOOD if self.rtt_ms < 60 else (COLOR_PING_WARN if self.rtt_ms < 150 else COLOR_PING_BAD)
                status_txt = f"EN VIVO ({active_node})"
                ping_txt = f"PING: {self.rtt_ms} ms"
            else:
                ping_color = (251, 146, 60)
                status_txt = f"FAILOVER -> {active_node}"
                ping_txt = "RECONECTANDO..."

            pygame.draw.rect(screen, (10, 14, 26), (WINDOW_WIDTH - 230, 12, 215, 60), border_radius=8)
            pygame.draw.rect(screen, ping_color, (WINDOW_WIDTH - 230, 12, 215, 60), 2, border_radius=8)
            screen.blit(font_mono.render(ping_txt, True, ping_color), (WINDOW_WIDTH - 215, 20))
            screen.blit(font_small.render(status_txt, True, ping_color), (WINDOW_WIDTH - 215, 44))

            # Banner no bloqueante de corte de red (Prueba del Profesor) - Posición Y:88 para evitar colisión
            if not self.is_connected and self.game_state == "PLAYING":
                banner_rect = pygame.Rect(WINDOW_WIDTH // 2 - 240, 88, 480, 22)
                pygame.draw.rect(screen, (154, 52, 18), banner_rect, border_radius=6)
                pygame.draw.rect(screen, (249, 115, 22), banner_rect, 1, border_radius=6)
                b_txt = font_small.render("[AVISO RED] Corte detectado: Modo contingencia local y reconexion activa", True, (255, 255, 255))
                screen.blit(b_txt, (WINDOW_WIDTH // 2 - b_txt.get_width() // 2, 91))

            # =============================================================
            # K. OVERLAYS DE ESTADO (INTRODUCCIÓN, DERROTA Y VICTORIA)
            # =============================================================
            if self.game_state == "INTRO":
                overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
                overlay.fill((10, 14, 26, 235))
                screen.blit(overlay, (0, 0))

                card_w, card_h = 760, 520
                cx = (WINDOW_WIDTH - card_w) // 2
                cy = (WINDOW_HEIGHT - card_h) // 2
                pygame.draw.rect(screen, (15, 23, 42), (cx, cy, card_w, card_h), border_radius=16)
                pygame.draw.rect(screen, (56, 189, 248), (cx, cy, card_w, card_h), 2, border_radius=16)

                t1 = font_title.render("EcoStream 3R - AquaGuardians: Crisis Hidrica", True, (56, 189, 248))
                screen.blit(t1, (cx + (card_w - t1.get_width()) // 2, cy + 22))

                sub = font_med.render("Mision Comunitaria: Gestiona los recursos hidricos y evita el colapso", True, (248, 250, 252))
                screen.blit(sub, (cx + (card_w - sub.get_width()) // 2, cy + 60))

                # 3 Pilares
                pills = [
                    ("1. REDUCIR (Zona Azul/Tuberias)", "Acercate a tuberias rotas y presiona [ESPACIO] para sellar fugas y salvar agua.", (248, 113, 113)),
                    ("2. REUSAR (Zona Verde/Huertos)", "Acercate al huerto y presiona [R] para canalizar aguas grises a los cultivos.", (134, 239, 172)),
                    ("3. RECICLAR (Zona Morada/Planta)", "Acercate a la planta y presiona [F] para activar filtros UV y restaurar pureza.", (216, 180, 254)),
                ]
                for idx, (p_title, p_desc, p_col) in enumerate(pills):
                    py = cy + 105 + idx * 72
                    pygame.draw.rect(screen, (30, 41, 59), (cx + 30, py, card_w - 60, 60), border_radius=10)
                    screen.blit(font_med.render(p_title, True, p_col), (cx + 45, py + 10))
                    screen.blit(font_small.render(p_desc, True, (226, 232, 240)), (cx + 45, py + 34))

                # Condiciones de derrota
                vy = cy + 335
                pygame.draw.rect(screen, (45, 10, 10), (cx + 30, vy, card_w - 60, 80), border_radius=10)
                pygame.draw.rect(screen, (239, 68, 68), (cx + 30, vy, card_w - 60, 80), 1, border_radius=10)
                screen.blit(font_med.render("[!] CONDICIONES DE DERROTA (GAME OVER):", True, (248, 113, 113)), (cx + 45, vy + 8))
                screen.blit(font_small.render("- Si el Embalse llega a 0.0% (Sequia Extrema por fugas desatendidas).", True, (254, 202, 202)), (cx + 45, vy + 30))
                screen.blit(font_small.render("- Si la Pureza cae por debajo de 40.0% (Contaminacion Toxica comunal).", True, (254, 202, 202)), (cx + 45, vy + 50))

                # Botón Comenzar
                by = cy + 440
                pygame.draw.rect(screen, (2, 132, 199), (cx + 180, by, 400, 50), border_radius=25)
                btn_txt = font_large.render("PRESIONA [ESPACIO] PARA INICIAR", True, (255, 255, 255))
                screen.blit(btn_txt, (cx + 180 + (400 - btn_txt.get_width()) // 2, by + 13))

            elif self.game_state == "GAMEOVER":
                overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
                overlay.fill((25, 5, 5, 235))
                screen.blit(overlay, (0, 0))

                card_w, card_h = 680, 380
                cx = (WINDOW_WIDTH - card_w) // 2
                cy = (WINDOW_HEIGHT - card_h) // 2
                pygame.draw.rect(screen, (30, 10, 10), (cx, cy, card_w, card_h), border_radius=16)
                pygame.draw.rect(screen, (239, 68, 68), (cx, cy, card_w, card_h), 3, border_radius=16)

                t_fail = font_large.render("MISIÓN FALLIDA - COLAPSO HÍDRICO", True, (239, 68, 68))
                screen.blit(t_fail, (cx + (card_w - t_fail.get_width()) // 2, cy + 30))

                reason_lines = self.game_over_reason.split("\n")
                for i, line in enumerate(reason_lines):
                    r_surf = font_med.render(line, True, (254, 202, 202))
                    screen.blit(r_surf, (cx + (card_w - r_surf.get_width()) // 2, cy + 85 + i * 26))

                stats_txt = f"Puntaje Final: {self.team_score} pts | Agua Salvada: {self.liters_saved:.0f} L"
                s_surf = font_med.render(stats_txt, True, (250, 204, 21))
                screen.blit(s_surf, (cx + (card_w - s_surf.get_width()) // 2, cy + 165))

                by = cy + 275
                pygame.draw.rect(screen, (185, 28, 28), (cx + 140, by, 400, 50), border_radius=25)
                re_txt = font_med.render("PRESIONA [R] O [ESPACIO] PARA REINTENTAR", True, (255, 255, 255))
                screen.blit(re_txt, (cx + 140 + (400 - re_txt.get_width()) // 2, by + 14))

            elif self.game_state == "VICTORY":
                overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
                overlay.fill((5, 25, 10, 235))
                screen.blit(overlay, (0, 0))

                card_w, card_h = 680, 380
                cx = (WINDOW_WIDTH - card_w) // 2
                cy = (WINDOW_HEIGHT - card_h) // 2
                pygame.draw.rect(screen, (10, 35, 20), (cx, cy, card_w, card_h), border_radius=16)
                pygame.draw.rect(screen, (34, 197, 94), (cx, cy, card_w, card_h), 3, border_radius=16)

                t_win = font_large.render("¡MISIÓN CUMPLIDA - COMUNIDAD SALVADA!", True, (34, 197, 94))
                screen.blit(t_win, (cx + (card_w - t_win.get_width()) // 2, cy + 30))

                msg_surf = font_med.render("Lograste preservar el suministro vital y contener las amenazas.", True, (220, 252, 231))
                screen.blit(msg_surf, (cx + (card_w - msg_surf.get_width()) // 2, cy + 85))

                stats_txt = f"Puntaje de Excelencia: {self.team_score} pts | Agua Salvada: {self.liters_saved:.0f} L"
                s_surf = font_med.render(stats_txt, True, (250, 204, 21))
                screen.blit(s_surf, (cx + (card_w - s_surf.get_width()) // 2, cy + 150))

                by = cy + 275
                pygame.draw.rect(screen, (22, 101, 52), (cx + 140, by, 400, 50), border_radius=25)
                re_txt = font_med.render("PRESIONA [R] O [ESPACIO] PARA JUGAR DE NUEVO", True, (255, 255, 255))
                screen.blit(re_txt, (cx + 140 + (400 - re_txt.get_width()) // 2, by + 14))

            pygame.display.flip()

        pygame.quit()
        self.running = False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EcoStream 3R - AquaGuardians: Cliente Multi-Host Resiliente (Pygame + gRPC)")
    parser.add_argument("--bot", action="store_true", help="Activa el modo bot automático con A* para pruebas de carga")
    parser.add_argument("--headless", action="store_true", help="Ejecutar en modo consola sin interfaz gráfica Pygame")
    parser.add_argument("--duration", type=float, default=None, help="Duración en segundos para la ejecución headless")
    parser.add_argument("--env", choices=["auto", "local", "cloud"], default="auto", help="Estrategia de conexión (auto: LAN mDNS/probe -> cloud)")
    parser.add_argument("--gateway", default="", help="URL del Gateway REST (ej: http://localhost:8080 o https://ecostream-gateway.onrender.com)")
    parser.add_argument("--host", default="", help="Host gRPC del motor de simulación primario (ej: localhost:50052)")
    parser.add_argument("--hosts", default="", help="Lista de hosts gRPC para failover separados por coma")
    parser.add_argument("--room", default="", help="Código o ID de la sala")
    parser.add_argument("--player", default="EcoPlayer_01", help="Nombre o ID del jugador")
    args = parser.parse_args()

    gateway_url = args.gateway
    engine_endpoint = args.host

    if not gateway_url:
        if args.env == "local":
            gateway_url = "http://localhost:8080"
            if not engine_endpoint:
                engine_endpoint = "localhost:50052"
            logger.info(f"[CONFIG] Entorno forzado a LOCAL: Gateway={gateway_url}, Engine={engine_endpoint}")
        elif args.env == "cloud":
            gateway_url = "https://ecostream-gateway.onrender.com"
            if not engine_endpoint:
                engine_endpoint = "ecostream-engine.onrender.com:443"
            logger.info(f"[CONFIG] Entorno forzado a CLOUD: Gateway={gateway_url}, Engine={engine_endpoint}")
        elif discover_servers:
            logger.info("[DISCOVERY] Buscando servidor local vía mDNS (_ecostream._tcp.local.) o HTTP...")
            gw, eng, mode = discover_servers(prefer_local=True)
            gateway_url = gw
            if not engine_endpoint:
                engine_endpoint = eng
            logger.info(f"[DISCOVERY] Servidor resuelto [{mode}]: Gateway={gateway_url}, Engine={engine_endpoint}")
        else:
            gateway_url = "http://localhost:8080"
            if not engine_endpoint:
                engine_endpoint = "localhost:50052"

    player_id = args.player
    room_id = args.room or "rm_demo_01"
    room_ticket = ""

    if gateway_url:
        try:
            logger.info(f"[AUTH] Autenticando jugador '{args.player}' en Gateway {gateway_url}...")
            _, auth_user, auth_room, ticket, sim_ep = authenticate_and_join_room(
                gateway_url=gateway_url,
                username=args.player,
                room_code=args.room
            )
            player_id = auth_user
            room_id = auth_room
            room_ticket = ticket
            if not engine_endpoint:
                engine_endpoint = sim_ep
            logger.info(f"✅ [AUTH] Sesión confirmada: ID={player_id}, Sala={room_id}, Ticket={room_ticket[:16]}...")
        except Exception as e:
            logger.warning(f"⚠️ [AUTH] No se pudo conectar con el Gateway ({e}). Continuando en modo directo/offline.")

    if not engine_endpoint:
        engine_endpoint = "localhost:50052"

    hosts = args.hosts or engine_endpoint

    client = EcoStreamGameClient(
        host=engine_endpoint,
        hosts=hosts,
        room_id=room_id,
        player_id=player_id,
        room_ticket=room_ticket,
        is_bot=args.bot
    )

    if args.headless:
        client.run_headless(duration_sec=args.duration)
    else:
        client.run()
