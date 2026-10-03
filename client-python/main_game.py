#!/usr/bin/env python3
"""
EcoStream 3R - AquaGuardians: Cliente de Videojuego en Tiempo Real (Pygame + gRPC)
Soporta:
1. Modo Jugador Humano (Teclado WASD / Flechas + Espacio para interactuar).
2. Modo Bot Autónomo (--bot) para pruebas de estrés y evaluación automática.
3. Telemetría de Latencia RTT Ping-Pong en vivo.
"""

import sys
import time
import math
import argparse
import threading
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
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 640
FPS = 60

# Paleta de Colores Ecológica (Aqua / Eco Pixel Art)
COLOR_BG = (15, 23, 42)          # Slate oscuro
COLOR_HUD_BG = (30, 41, 59)      # Panel superior
COLOR_RESERVOIR = (14, 165, 233)  # Azul agua cristalina
COLOR_RESERVOIR_BG = (12, 74, 110)
COLOR_PURITY = (52, 211, 153)    # Verde esmeralda ecológico
COLOR_PIPE_OK = (100, 116, 139)  # Gris tubería metálica
COLOR_PIPE_LEAK = (239, 68, 68)  # Rojo fuga activa
COLOR_VALVE = (245, 158, 11)     # Amarillo compuerta
COLOR_PLANT = (168, 85, 247)     # Púrpura planta biológica
COLOR_PLAYER = (59, 130, 246)    # Azul avatar
COLOR_BOT = (236, 72, 153)       # Rosa avatar bot
COLOR_TEXT = (241, 245, 249)
COLOR_PING_GOOD = (34, 197, 94)  # Verde < 60ms
COLOR_PING_WARN = (234, 179, 8)  # Amarillo < 150ms
COLOR_PING_BAD = (239, 68, 68)   # Rojo > 150ms

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
        self.player_x = 200.0
        self.player_y = 300.0
        self.pipes = []
        self.valves = []
        self.plants = []

        # Cola de acciones hacia Rust
        self.action_queue = []
        self.lock = threading.Lock()

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
                    # Mensaje inicial
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

            except Exception as e:
                self.is_connected = False
                time.sleep(2.0) # Reintento de reconexión

    def queue_action(self, action):
        with self.lock:
            self.action_queue.append(action)

    def bot_ai_tick(self):
        """Lógica de IA del Bot para pruebas automáticas de estrés y 3R"""
        # 1. Prioridad: Buscar tubería con fuga más cercana (REDUCIR)
        leaking_pipes = [p for p in self.pipes if p.is_leaking]
        if leaking_pipes:
            target = leaking_pipes[0]
            tx = target.position.x * 15.0 + 100.0
            ty = target.position.y * 8.0 + 150.0

            # Mover hacia la fuga
            dx = tx - self.player_x
            dy = ty - self.player_y
            dist = math.hypot(dx, dy)

            if dist > 30.0:
                self.player_x += (dx / dist) * 4.0
                self.player_y += (dy / dist) * 4.0
            else:
                # Reparar fuga (1. REDUCIR)
                self.queue_action(gameplay_pb2.PlayerAction(
                    action_id=int(time.time()*1000),
                    repair_pipe=gameplay_pb2.RepairPipeAction(pipe_id=target.pipe_id, repair_progress_delta=35.0)
                ))
            return

        # 2. Reusar o Reciclar si no hay fugas
        if self.tick % 40 == 0 and self.valves:
            self.queue_action(gameplay_pb2.PlayerAction(
                action_id=int(time.time()*1000),
                divert_valve=gameplay_pb2.DivertValveAction(valve_id=1, destination=gameplay_pb2.DESTINATION_IRRIGATION)
            ))
        elif self.tick % 60 == 0 and self.plants:
            self.queue_action(gameplay_pb2.PlayerAction(
                action_id=int(time.time()*1000),
                operate_recycle=gameplay_pb2.OperateRecycleAction(plant_id=1, operation=gameplay_pb2.OperateRecycleAction.RECYCLE_OP_LOAD_FILTER)
            ))

    def run(self):
        pygame.init()
        pygame.font.init()
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        mode_title = "MODO BOT AUTOMATICO (Stress Testing)" if self.is_bot else "MODO JUGADOR INTERACTIVO"
        pygame.display.set_caption(f"EcoStream 3R - AquaGuardians [{mode_title}]")
        clock = pygame.time.Clock()

        font_large = pygame.font.SysFont("Segoe UI", 20, bold=True)
        font_med = pygame.font.SysFont("Segoe UI", 15, bold=True)
        font_small = pygame.font.SysFont("Segoe UI", 12)

        running = True
        wave_anim = 0

        while running:
            dt = clock.tick(FPS) / 1000.0
            wave_anim += dt * 3.0

            # -------------------------------------------------------------
            # 1. EVENTOS Y ENTRADA DE USUARIO
            # -------------------------------------------------------------
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif not self.is_bot and event.key == pygame.K_SPACE:
                        # 1. Acción Reparar Fuga más cercana (REDUCIR)
                        if self.pipes:
                            for p in self.pipes:
                                if p.is_leaking:
                                    self.queue_action(gameplay_pb2.PlayerAction(
                                        action_id=int(time.time()*1000),
                                        repair_pipe=gameplay_pb2.RepairPipeAction(pipe_id=p.pipe_id, repair_progress_delta=50.0)
                                    ))
                                    break
                    elif not self.is_bot and event.key == pygame.K_r:
                        # 2. Acción Reusar aguas grises (REUSAR)
                        self.queue_action(gameplay_pb2.PlayerAction(
                            action_id=int(time.time()*1000),
                            divert_valve=gameplay_pb2.DivertValveAction(valve_id=1, destination=gameplay_pb2.DESTINATION_IRRIGATION)
                        ))
                    elif not self.is_bot and event.key == pygame.K_f:
                        # 3. Acción Reciclar planta biológica (RECICLAR)
                        self.queue_action(gameplay_pb2.PlayerAction(
                            action_id=int(time.time()*1000),
                            operate_recycle=gameplay_pb2.OperateRecycleAction(plant_id=1, operation=gameplay_pb2.OperateRecycleAction.RECYCLE_OP_LOAD_FILTER)
                        ))

            # Movimiento continuo con teclas (si no es bot)
            if not self.is_bot:
                keys = pygame.key.get_pressed()
                speed = 220.0 * dt
                if keys[pygame.K_w] or keys[pygame.K_UP]:
                    self.player_y = max(120, self.player_y - speed)
                if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                    self.player_y = min(WINDOW_HEIGHT - 40, self.player_y + speed)
                if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                    self.player_x = max(40, self.player_x - speed)
                if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                    self.player_x = min(WINDOW_WIDTH - 40, self.player_x + speed)
            else:
                self.bot_ai_tick()

            # -------------------------------------------------------------
            # 2. RENDERIZADO GRÁFICO (Top-Down Pixel Art Style)
            # -------------------------------------------------------------
            screen.fill(COLOR_BG)

            # A. ZONA DEL EMBALSE PRINCIPAL (Izquierda)
            res_rect = pygame.Rect(40, 130, 240, 460)
            pygame.draw.rect(screen, COLOR_RESERVOIR_BG, res_rect, border_radius=12)
            water_height = int(460 * (self.reservoir_pct / 100.0))
            water_rect = pygame.Rect(40, 130 + (460 - water_height), 240, water_height)
            pygame.draw.rect(screen, COLOR_RESERVOIR, water_rect, border_radius=12)
            pygame.draw.rect(screen, (56, 189, 248), res_rect, 3, border_radius=12)

            res_label = font_med.render(f"💧 EMBALSE: {self.reservoir_pct:.1f}%", True, COLOR_TEXT)
            screen.blit(res_label, (55, 140))

            # B. ZONA 1: REDUCIR (Tuberías y Fugas)
            pygame.draw.rect(screen, (30, 41, 59), (320, 130, 280, 220), border_radius=10)
            pygame.draw.rect(screen, (71, 85, 105), (320, 130, 280, 220), 2, border_radius=10)
            screen.blit(font_med.render("1. REDUCIR (Fugas Comunales)", True, (248, 113, 113)), (335, 140))

            for i, p in enumerate(self.pipes):
                py_y = 180 + i * 50
                p_color = COLOR_PIPE_LEAK if p.is_leaking else COLOR_PIPE_OK
                pygame.draw.rect(screen, p_color, (340, py_y, 240, 30), border_radius=6)
                txt = f"Tubería #{p.pipe_id}: {'¡ROTURA/FUGA!' if p.is_leaking else 'Sellada (OK)'}"
                screen.blit(font_small.render(txt, True, (255, 255, 255)), (350, py_y + 7))

            # C. ZONA 2: REUSAR (Huertos y Desvío de Aguas Grises)
            pygame.draw.rect(screen, (20, 83, 45), (320, 370, 280, 220), border_radius=10)
            pygame.draw.rect(screen, (34, 197, 94), (320, 370, 280, 220), 2, border_radius=10)
            screen.blit(font_med.render("2. REUSAR (Huerto Comunitario)", True, (134, 239, 172)), (335, 380))
            screen.blit(font_small.render("Válvula Aguas Grises -> Riego Activo 🌱", True, COLOR_TEXT), (335, 410))
            screen.blit(font_small.render(f"Reuso acumulado: {self.liters_reused:.0f} Litros", True, (200, 250, 200)), (335, 435))

            # D. ZONA 3: RECICLAR (Planta de Filtrado Biológico)
            pygame.draw.rect(screen, (88, 28, 135), (630, 130, 290, 460), border_radius=10)
            pygame.draw.rect(screen, (168, 85, 247), (630, 130, 290, 460), 2, border_radius=10)
            screen.blit(font_med.render("3. RECICLAR (Planta Filtrado)", True, (216, 180, 254)), (645, 140))
            screen.blit(font_small.render(f"Pureza Hídrica: {self.purity_pct:.1f}%", True, COLOR_PURITY), (645, 180))
            screen.blit(font_small.render(f"Descontaminado: {self.liters_recycled:.0f} Litros", True, COLOR_TEXT), (645, 210))
            screen.blit(font_small.render("Filtro: Carbón Activo & Grava", True, (192, 132, 252)), (645, 240))

            # E. AVATAR DEL JUGADOR / BOT
            avatar_color = COLOR_BOT if self.is_bot else COLOR_PLAYER
            pygame.draw.circle(screen, avatar_color, (int(self.player_x), int(self.player_y)), 18)
            pygame.draw.circle(screen, (255, 255, 255), (int(self.player_x), int(self.player_y)), 18, 2)
            lbl = "BOT" if self.is_bot else "TÚ"
            screen.blit(font_small.render(lbl, True, (255, 255, 255)), (int(self.player_x) - 10, int(self.player_y) - 8))

            # F. PANEL HUD SUPERIOR (Telemetría en Vivo & RTT)
            pygame.draw.rect(screen, COLOR_HUD_BG, (0, 0, WINDOW_WIDTH, 100))
            pygame.draw.line(screen, (51, 65, 85), (0, 100), (WINDOW_WIDTH, 100), 2)

            # Título y Sala
            screen.blit(font_large.render("EcoStream 3R - AquaGuardians", True, (56, 189, 248)), (20, 15))
            screen.blit(font_small.render(f"Lobby: [{self.room_id}] | Modo: {mode_title}", True, (148, 163, 184)), (20, 45))
            screen.blit(font_small.render("Controles: [WASD] Mover | [Espacio] 1.Reducir | [R] 2.Reusar | [F] 3.Reciclar", True, (203, 213, 225)), (20, 70))

            # Score y Ahorro
            screen.blit(font_med.render(f"PUNTAJE: {self.team_score}", True, (250, 204, 21)), (450, 20))
            screen.blit(font_small.render(f"Ahorro Fugas: {self.liters_saved:.0f} L", True, (52, 211, 153)), (450, 45))
            screen.blit(font_small.render(f"Tiempo: {self.remaining_seconds}s | Tick: #{self.tick}", True, (148, 163, 184)), (450, 70))

            # Widget de Latencia RTT Ping-Pong en vivo (Verde/Amarillo/Rojo)
            ping_color = COLOR_PING_GOOD if self.rtt_ms < 60 else (COLOR_PING_WARN if self.rtt_ms < 150 else COLOR_PING_BAD)
            pygame.draw.rect(screen, (15, 23, 42), (WINDOW_WIDTH - 220, 15, 200, 70), border_radius=8)
            pygame.draw.rect(screen, ping_color, (WINDOW_WIDTH - 220, 15, 200, 70), 2, border_radius=8)

            screen.blit(font_med.render(f"PING: {self.rtt_ms} ms", True, ping_color), (WINDOW_WIDTH - 205, 25))
            status_txt = "CONECTADO A RUST 20Hz" if self.is_connected else "RECONECTANDO..."
            screen.blit(font_small.render(status_txt, True, ping_color), (WINDOW_WIDTH - 205, 52))

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
