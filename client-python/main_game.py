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
import argparse
import threading
from typing import List, Tuple, Optional, Set
from pathlib import Path

# Configurar path de stubs proto
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "client-python" / "proto"))

import grpc
import pygame
from ecostream.v1 import common_pb2
from ecostream.v1 import gameplay_pb2
from ecostream.v1 import gameplay_pb2_grpc

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
    def __init__(self, host="localhost:50052", room_id="rm_demo_01", player_id="usr_victor", is_bot=False):
        self.host = host
        self.room_id = room_id
        self.player_id = player_id
        self.is_bot = is_bot

        # Estado del juego sincronizado desde Rust (20Hz)
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

        # Entidades locales
        self.player_x = 380.0
        self.player_y = 320.0
        self.pipes = []
        self.valves = []
        self.plants = []

        # Cola de acciones hacia Rust
        self.action_queue = []
        self.lock = threading.Lock()

        # Efectos visuales
        self.particles = []
        self.floating_texts = []

        # Iniciar hilo de comunicación gRPC
        self.grpc_thread = threading.Thread(target=self._run_grpc_stream, daemon=True)
        self.grpc_thread.start()

    def _run_grpc_stream(self):
        """Streaming bidireccional continuo con el Servidor Rust (20 Hz)"""
        while True:
            try:
                channel = grpc.insecure_channel(self.host)
                stub = gameplay_pb2_grpc.GameSimulationServiceStub(channel)
                self.is_connected = True

                def request_generator():
                    t_now = int(time.time() * 1000)
                    yield gameplay_pb2.ClientStreamMessage(
                        room_id=self.room_id,
                        player_id=self.player_id,
                        client_tick=1,
                        ping=common_pb2.PingMessage(client_timestamp_ms=t_now, sequence_id=1)
                    )

                    client_tick = 1
                    while True:
                        time.sleep(0.05) # 20 Hz
                        client_tick += 1
                        t_now = int(time.time() * 1000)

                        action = None
                        with self.lock:
                            if self.action_queue:
                                action = self.action_queue.pop(0)

                        msg = gameplay_pb2.ClientStreamMessage(
                            room_id=self.room_id,
                            player_id=self.player_id,
                            client_tick=client_tick,
                            action=action,
                            ping=common_pb2.PingMessage(client_timestamp_ms=t_now, sequence_id=client_tick)
                        )
                        yield msg

                responses = stub.StreamGame(request_generator())
                for resp in responses:
                    if resp.HasField("initial_snapshot"):
                        self.reconnect_ticket = resp.initial_snapshot.reconnect_ticket

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
                        self.pipes = ws.pipes
                        self.valves = ws.valves
                        self.plants = ws.plants

                    if resp.HasField("pong"):
                        self.rtt_ms = int(time.time() * 1000) - resp.pong.echo_client_timestamp_ms

            except Exception:
                self.is_connected = False
                time.sleep(2.0)

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
            self.floating_texts.append(FloatingText("+100 PTS [A* Filtro UV ⚗️]", self.player_x - 30, self.player_y - 20, (192, 132, 252)))

    def run(self):
        pygame.init()
        pygame.font.init()
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        mode_title = "MODO BOT AUTOMÁTICO" if self.is_bot else "MODO JUGADOR AQUAGUARDIAN"
        pygame.display.set_caption(f"EcoStream 3R - AquaGuardians [{mode_title}]")
        clock = pygame.time.Clock()

        font_large = pygame.font.SysFont("Segoe UI", 20, bold=True)
        font_med = pygame.font.SysFont("Segoe UI", 14, bold=True)
        font_small = pygame.font.SysFont("Segoe UI", 12)
        font_mono = pygame.font.SysFont("Consolas", 13, bold=True)

        running = True
        wave_time = 0.0

        while running:
            dt = clock.tick(FPS) / 1000.0
            wave_time += dt * 3.5

            # Eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif not self.is_bot and event.key == pygame.K_SPACE:
                        # 1. Reducir
                        if self.pipes:
                            for p in self.pipes:
                                if p.is_leaking:
                                    self.spawn_sparks(self.player_x, self.player_y)
                                    self.queue_action(gameplay_pb2.PlayerAction(
                                        action_id=int(time.time()*1000),
                                        repair_pipe=gameplay_pb2.RepairPipeAction(pipe_id=p.pipe_id, repair_progress_delta=50.0)
                                    ))
                                    self.floating_texts.append(FloatingText("+150 PTS (Fuga Reparada!)", self.player_x - 40, self.player_y - 20, (56, 189, 248)))
                                    break
                    elif not self.is_bot and event.key == pygame.K_r:
                        # 2. Reusar
                        self.queue_action(gameplay_pb2.PlayerAction(
                            action_id=int(time.time()*1000),
                            divert_valve=gameplay_pb2.DivertValveAction(valve_id=1, destination=gameplay_pb2.DESTINATION_IRRIGATION)
                        ))
                        self.floating_texts.append(FloatingText("+80 PTS (Riego de Huerto 🌱)", self.player_x - 40, self.player_y - 20, (52, 211, 153)))
                    elif not self.is_bot and event.key == pygame.K_f:
                        # 3. Reciclar
                        self.queue_action(gameplay_pb2.PlayerAction(
                            action_id=int(time.time()*1000),
                            operate_recycle=gameplay_pb2.OperateRecycleAction(plant_id=1, operation=gameplay_pb2.OperateRecycleAction.RECYCLE_OP_LOAD_FILTER)
                        ))
                        self.floating_texts.append(FloatingText("+120 PTS (Filtro Carbón UV ⚗️)", self.player_x - 40, self.player_y - 20, (192, 132, 252)))

            # Movimiento Jugador / Bot
            if not self.is_bot:
                keys = pygame.key.get_pressed()
                speed = 240.0 * dt
                if keys[pygame.K_w] or keys[pygame.K_UP]: self.player_y = max(110, self.player_y - speed)
                if keys[pygame.K_s] or keys[pygame.K_DOWN]: self.player_y = min(WINDOW_HEIGHT - 35, self.player_y + speed)
                if keys[pygame.K_a] or keys[pygame.K_LEFT]: self.player_x = max(35, self.player_x - speed)
                if keys[pygame.K_d] or keys[pygame.K_RIGHT]: self.player_x = min(WINDOW_WIDTH - 35, self.player_x + speed)
            else:
                self.bot_ai_tick()

            # Partículas de fugas
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
            # RENDERIZADO
            # -------------------------------------------------------------
            screen.fill(COLOR_BG)

            # A. EMBALSE PRINCIPAL
            res_rect = pygame.Rect(30, 110, 240, 530)
            pygame.draw.rect(screen, COLOR_RESERVOIR_BG, res_rect, border_radius=14)
            
            fill_h = int(500 * (max(2.0, self.reservoir_pct) / 100.0))
            water_rect = pygame.Rect(30, 110 + (530 - fill_h), 240, fill_h)
            pygame.draw.rect(screen, COLOR_RESERVOIR, water_rect, border_radius=14)
            pygame.draw.rect(screen, COLOR_PANEL_BORDER, res_rect, 2, border_radius=14)

            # Ondas decorativas
            for ox in range(35, 265, 8):
                oy = 110 + (530 - fill_h) + int(math.sin(ox * 0.08 + wave_time) * 3.0)
                pygame.draw.circle(screen, (255, 255, 255), (ox, oy), 2)

            screen.blit(font_med.render(f"💧 EMBALSE: {self.reservoir_pct:.1f}%", True, COLOR_TEXT), (45, 125))

            # B. ZONA 1: REDUCIR
            z1 = pygame.Rect(300, 110, 290, 250)
            pygame.draw.rect(screen, (22, 32, 54), z1, border_radius=12)
            pygame.draw.rect(screen, (71, 85, 105), z1, 2, border_radius=12)
            screen.blit(font_med.render("🔧 1. REDUCIR (Fugas)", True, (248, 113, 113)), (315, 122))

            for i, p in enumerate(self.pipes):
                py_y = 160 + i * 55
                p_color = COLOR_PIPE_LEAK if p.is_leaking else COLOR_PIPE_OK
                pygame.draw.rect(screen, p_color, (315, py_y, 260, 36), border_radius=6)
                txt = f"Tubería #{p.pipe_id}: {'⚠️ ¡FUGA CRÍTICA!' if p.is_leaking else 'Presión Normal (OK)'}"
                screen.blit(font_small.render(txt, True, (255, 255, 255)), (325, py_y + 9))

            # C. ZONA 2: REUSAR
            z2 = pygame.Rect(300, 380, 290, 260)
            pygame.draw.rect(screen, (20, 83, 45), z2, border_radius=12)
            pygame.draw.rect(screen, (34, 197, 94), z2, 2, border_radius=12)
            screen.blit(font_med.render("🌱 2. REUSAR (Huertos Comunitarios)", True, (134, 239, 172)), (315, 395))
            screen.blit(font_small.render(f"Reuso acumulado: {self.liters_reused:.0f} L", True, (220, 252, 231)), (315, 425))
            screen.blit(font_small.render("Válvula de aguas grises canalizada a riego", True, COLOR_TEXT_MUTED), (315, 450))

            # D. ZONA 3: RECICLAR
            z3 = pygame.Rect(615, 110, 380, 530)
            pygame.draw.rect(screen, (46, 16, 77), z3, border_radius=12)
            pygame.draw.rect(screen, COLOR_PLANT, z3, 2, border_radius=12)
            screen.blit(font_med.render("⚗️ 3. RECICLAR (Planta Filtrado UV)", True, (216, 180, 254)), (630, 125))
            screen.blit(font_med.render(f"Pureza Hídrica: {self.purity_pct:.1f}%", True, COLOR_PURITY), (630, 160))
            screen.blit(font_small.render(f"Agua Descontaminada: {self.liters_recycled:.0f} L", True, (243, 232, 255)), (630, 190))

            # Filtro rotatorio central
            center_x, center_y = 800, 380
            pygame.draw.circle(screen, (168, 85, 247), (center_x, center_y), 50, 3)
            for a in range(4):
                ang = wave_time + a * (math.pi / 2.0)
                fx = center_x + int(math.cos(ang) * 40)
                fy = center_y + int(math.sin(ang) * 40)
                pygame.draw.line(screen, (216, 180, 254), (center_x, center_y), (fx, fy), 2)

            # E. PARTÍCULAS
            self.particles = [p for p in self.particles if p.update()]
            for p in self.particles:
                pygame.draw.circle(screen, p.color, (int(p.x), int(p.y)), p.size)

            # F. AVATAR
            avatar_col = COLOR_BOT if self.is_bot else COLOR_PLAYER
            pygame.draw.circle(screen, avatar_col, (int(self.player_x), int(self.player_y)), 18)
            pygame.draw.circle(screen, (255, 255, 255), (int(self.player_x), int(self.player_y)), 18, 2)
            lbl = "BOT" if self.is_bot else "TÚ"
            screen.blit(font_small.render(lbl, True, (255, 255, 255)), (int(self.player_x) - 10, int(self.player_y) - 8))

            # G. TEXTOS FLOTANTES
            self.floating_texts = [ft for ft in self.floating_texts if ft.update()]
            for ft in self.floating_texts:
                screen.blit(font_med.render(ft.text, True, ft.color), (int(ft.x), int(ft.y)))

            # H. HUD SUPERIOR
            pygame.draw.rect(screen, COLOR_PANEL_BG, (0, 0, WINDOW_WIDTH, 85))
            pygame.draw.line(screen, (51, 65, 85), (0, 85), (WINDOW_WIDTH, 85), 2)

            screen.blit(font_large.render("EcoStream 3R", True, (56, 189, 248)), (25, 12))
            screen.blit(font_small.render(f"Lobby: [{self.room_id}] | {mode_title}", True, COLOR_TEXT_MUTED), (25, 38))
            screen.blit(font_small.render("Controles: [WASD] Mover | [Espacio] 1.Reducir | [R] 2.Reusar | [F] 3.Reciclar", True, (203, 213, 225)), (25, 58))

            screen.blit(font_large.render(f"PUNTOS: {self.team_score}", True, (250, 204, 21)), (450, 15))
            screen.blit(font_small.render(f"Ahorro: {self.liters_saved:.0f} L | Tiempo: {self.remaining_seconds}s", True, (52, 211, 153)), (450, 45))

            # Widget Ping
            ping_color = COLOR_PING_GOOD if self.rtt_ms < 60 else (COLOR_PING_WARN if self.rtt_ms < 150 else COLOR_PING_BAD)
            pygame.draw.rect(screen, (10, 14, 26), (WINDOW_WIDTH - 200, 12, 175, 60), border_radius=8)
            pygame.draw.rect(screen, ping_color, (WINDOW_WIDTH - 200, 12, 175, 60), 2, border_radius=8)
            screen.blit(font_mono.render(f"PING: {self.rtt_ms} ms", True, ping_color), (WINDOW_WIDTH - 185, 20))
            status_txt = "EN VIVO 20Hz" if self.is_connected else "RECONECTANDO"
            screen.blit(font_small.render(status_txt, True, ping_color), (WINDOW_WIDTH - 185, 44))

            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EcoStream 3R - Cliente de Juego")
    parser.add_argument("--bot", action="store_true", help="Activa el modo bot automático para pruebas de carga")
    parser.add_argument("--host", default="localhost:50052", help="Host gRPC del motor Rust")
    parser.add_argument("--room", default="rm_demo_01", help="ID de la sala")
    parser.add_argument("--player", default="usr_victor_admin", help="ID del jugador")
    args = parser.parse_args()

    client = EcoStreamGameClient(
        host=args.host,
        room_id=args.room,
        player_id=args.player,
        is_bot=args.bot
    )
    client.run()
