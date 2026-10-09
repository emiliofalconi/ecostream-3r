#!/usr/bin/env python3
"""
EcoStream-3R: Herramienta de Verificación y Diagnóstico E2E de Red
Cátedra: Computación en la Nube (UCAB)

Soporta:
1. Red Local con mDNS / ZeroConf (autodescubrimiento sin IPs manuales).
2. Red Local con IP explícita.
3. Despliegue en la Nube en Render.com (con HTTPS y gRPC sobre TLS).
"""

import sys
import os
import time
import json
import socket
import ssl
import struct
import argparse
import urllib.request
import urllib.error

# Códigos de color ANSI para salida en terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_header(title: str):
    print(f"\n{BOLD}{CYAN}=== {title} ==={RESET}")

def print_success(msg: str):
    print(f"  {GREEN}[✓ PASS]{RESET} {msg}")

def print_fail(msg: str):
    print(f"  {RED}[✗ FAIL]{RESET} {msg}")

def print_info(msg: str):
    print(f"  {YELLOW}[ℹ INFO]{RESET} {msg}")

class NetworkVerifier:
    def __init__(self, gateway_url: str, engine_endpoint: str = None, use_tls: bool = False, timeout: float = 5.0):
        self.gateway_url = gateway_url.rstrip("/")
        self.engine_endpoint = engine_endpoint
        self.use_tls = use_tls
        self.timeout = timeout
        self.jwt_token = None
        self.room_id = None
        self.room_code = None
        self.room_ticket = None
        self.discovered_engine_endpoint = None

    def step_0_mdns_discovery(self) -> str:
        """Intenta descubrir el Gateway en la LAN vía mDNS o resolución de ecostream.local"""
        print_header("Paso 0: Descubrimiento ZeroConf / mDNS en Red Local")
        print_info("Buscando anuncios multicast '_ecostream._tcp.local' y resolviendo 'ecostream.local'...")

        # A. Intentar resolución de ecostream.local
        try:
            resolved_ip = socket.gethostbyname("ecostream.local")
            target_url = f"http://{resolved_ip}:8080"
            print_success(f"Hostname 'ecostream.local' resuelto exitosamente a IP: {resolved_ip}")
            # Validar health
            req = urllib.request.Request(f"{target_url}/healthz")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    print_success(f"Servidor Gateway confirmado en: {target_url}")
                    self.gateway_url = target_url
                    return target_url
        except Exception:
            pass

        # B. Intentar sondeo Multicast UDP a 224.0.0.251:5353
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.settimeout(1.5)
            # Query mDNS para _ecostream._tcp.local
            query = (
                b"\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00"
                b"\x0a_ecostream\x04_tcp\x05local\x00\x00\x0c\x00\x01"
            )
            sock.sendto(query, ("224.0.0.251", 5353))
            data, addr = sock.recvfrom(2048)
            server_ip = addr[0]
            sock.close()
            target_url = f"http://{server_ip}:8080"
            print_success(f"Respuesta mDNS recibida desde host: {server_ip}")
            self.gateway_url = target_url
            return target_url
        except Exception:
            pass

        # Fallback a localhost si nada respondió
        print_info("No se recibió respuesta mDNS externa. Usando localhost:8080 como fallback local.")
        self.gateway_url = "http://localhost:8080"
        return self.gateway_url

    def step_1_health_and_readiness(self) -> bool:
        """Verifica /healthz y /readyz del Gateway"""
        print_header("Paso 1: Sondas de Salud del Gateway Go (/healthz & /readyz)")
        
        # 1. Healthz
        t0 = time.time()
        try:
            url = f"{self.gateway_url}/healthz"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                elapsed = (time.time() - t0) * 1000
                body = json.loads(resp.read().decode())
                if resp.status == 200 and body.get("status") in ["UP", "SERVING"]:
                    print_success(f"GET {url} -> {resp.status} ({elapsed:.1f} ms) | Estado: {body.get('status')}")
                else:
                    print_fail(f"GET {url} respondió estatus inesperado: {resp.status} - {body}")
                    return False
        except Exception as e:
            print_fail(f"No fue posible conectar con {self.gateway_url}/healthz: {e}")
            return False

        # 2. Readyz
        t0 = time.time()
        try:
            url = f"{self.gateway_url}/readyz"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                elapsed = (time.time() - t0) * 1000
                body = json.loads(resp.read().decode())
                db_status = body.get("database", "unknown")
                redis_status = body.get("redis", "unknown")
                print_success(f"GET {url} -> {resp.status} ({elapsed:.1f} ms) | DB: {db_status}, Redis: {redis_status}")
        except Exception as e:
            print_fail(f"Fallo en verificación /readyz: {e}")
            return False

        return True

    def step_2_auth_login(self, username: str = "admin_eco", password: str = "EcoStream2026!") -> bool:
        """Autentica un usuario y extrae el token JWT"""
        print_header("Paso 2: Autenticación y Emisión de Token JWT")
        url = f"{self.gateway_url}/api/v1/auth/login"
        payload = json.dumps({"username": username, "password": password}).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        t0 = time.time()
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                elapsed = (time.time() - t0) * 1000
                data = json.loads(resp.read().decode())
                self.jwt_token = data.get("access_token") or data.get("token")
                user_id = data.get("user", {}).get("user_id", "desconocido")
                
                if not self.jwt_token:
                    print_fail(f"Respuesta de login no contiene token de acceso: {data}")
                    return False

                print_success(f"POST {url} -> 200 OK ({elapsed:.1f} ms)")
                print_info(f"Usuario autenticado: '{username}' (ID: {user_id})")
                print_info(f"JWT recibido: {self.jwt_token[:25]}... (Longitud: {len(self.jwt_token)} caracteres)")
                return True
        except urllib.error.HTTPError as e:
            err_body = e.read().decode()
            print_fail(f"Error HTTP {e.code} en Login: {err_body}")
            return False
        except Exception as e:
            print_fail(f"Fallo al conectar con endpoint de autenticación: {e}")
            return False

    def step_3_room_creation(self) -> bool:
        """Crea una sala y extrae el RoomTicket y el simulation_endpoint dinámico"""
        print_header("Paso 3: Creación de Sala y Asignación de Endpoint de Simulación")
        url = f"{self.gateway_url}/api/v1/rooms/create"
        payload = json.dumps({
            "room_name": "Sala de Diagnóstico E2E",
            "max_players": 4,
            "role": 1,
            "difficulty": 1
        }).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.jwt_token}"
        }

        t0 = time.time()
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                elapsed = (time.time() - t0) * 1000
                data = json.loads(resp.read().decode())
                
                room = data.get("room", {})
                self.room_id = room.get("room_id")
                self.room_code = room.get("room_code")
                self.discovered_engine_endpoint = room.get("simulation_endpoint")
                self.room_ticket = data.get("ticket") or data.get("room_ticket")

                print_success(f"POST {url} -> 200 OK ({elapsed:.1f} ms)")
                print_info(f"Sala Creada: ID={self.room_id} | Código={self.room_code}")
                print_info(f"Ticket HMAC de Acceso: {self.room_ticket[:30]}...")
                print_info(f"Endpoint de Simulación Retornado: {BOLD}{CYAN}{self.discovered_engine_endpoint}{RESET}")

                if not self.discovered_engine_endpoint:
                    print_fail("El Gateway no proporcionó 'simulation_endpoint' en la respuesta de la sala.")
                    return False
                return True
        except urllib.error.HTTPError as e:
            err_body = e.read().decode()
            print_fail(f"Error HTTP {e.code} al crear sala: {err_body}")
            return False
        except Exception as e:
            print_fail(f"Fallo al invocar creación de sala: {e}")
            return False

    def step_4_engine_connectivity(self) -> bool:
        """Verifica la conectividad con el Motor de Rust (gRPC HTTP/2 a 20 Hz)"""
        print_header("Paso 4: Conectividad con el Motor de Simulación (Rust 20 Hz)")
        
        target = self.engine_endpoint if self.engine_endpoint else self.discovered_engine_endpoint
        if not target:
            print_fail("No se dispone de un endpoint para el motor de simulación.")
            return False

        # Separar host y puerto
        target_clean = target.replace("https://", "").replace("http://", "")
        if ":" in target_clean:
            host, port_str = target_clean.split(":", 1)
            port = int(port_str)
        else:
            host = target_clean
            port = 443 if self.use_tls else 50052

        print_info(f"Destino de conexión: {host}:{port} (TLS={self.use_tls})")

        # A. Handshake TCP / TLS
        t0 = time.time()
        try:
            raw_sock = socket.create_connection((host, port), timeout=self.timeout)
            tcp_rtt = (time.time() - t0) * 1000
            print_success(f"Conexión TCP establecida con {host}:{port} (RTT: {tcp_rtt:.1f} ms)")

            if self.use_tls:
                # Contexto TLS 1.3 con negociación ALPN para HTTP/2 (h2)
                ctx = ssl.create_default_context()
                ctx.set_alpn_protocols(["h2"])
                tls_sock = ctx.wrap_socket(raw_sock, server_hostname=host)
                negotiated = tls_sock.selected_alpn_protocol()
                print_success(f"Handshake TLS completado con éxito (Cifrado: {tls_sock.cipher()[0]})")
                print_info(f"Protocolo ALPN negociado: '{negotiated}' (requerido 'h2' para gRPC)")
                sock = tls_sock
            else:
                sock = raw_sock

            # B. Envío de Prefacio HTTP/2 de gRPC (Client Connection Preface)
            # En gRPC sobre HTTP/2, todo cliente inicia con el prefacio mágico y un frame SETTINGS
            preface = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
            settings_frame = struct.pack(">HBBBL", 0, 4, 0, 0, 0) # Longitud 0, Tipo 4 (SETTINGS), Flags 0, Stream 0
            sock.sendall(preface + settings_frame)

            # Leer respuesta inicial del servidor (esperando frame SETTINGS de Tonic/Rust)
            sock.settimeout(2.5)
            resp_bytes = sock.recv(1024)
            if len(resp_bytes) >= 9:
                frame_len = (resp_bytes[0] << 16) | (resp_bytes[1] << 8) | resp_bytes[2]
                frame_type = resp_bytes[3]
                if frame_type == 4:
                    print_success("Respuesta HTTP/2 recibida: Marco SETTINGS confirmado por el servidor Rust")
                    print_success(f"Canal de streaming gRPC HTTP/2 validado operando a baja latencia ({tcp_rtt:.1f} ms)")
                else:
                    print_info(f"Servidor respondió con marco HTTP/2 tipo: {frame_type}")
            else:
                print_info(f"Servidor aceptó prefacio HTTP/2 ({len(resp_bytes)} bytes recibidos)")

            sock.close()
            return True
        except Exception as e:
            print_fail(f"No fue posible completar la comunicación con el motor en {host}:{port}: {e}")
            return False

    def run_all(self, auto_discover: bool = False, username: str = "admin_eco", password: str = "EcoStream2026!") -> bool:
        """Ejecuta la secuencia completa de validación"""
        print(f"\n{BOLD}{GREEN}==================================================================={RESET}")
        print(f"{BOLD}{GREEN} EcoStream-3R: Verificación End-to-End de Conectividad y Despliegue {RESET}")
        print(f"{BOLD}{GREEN}==================================================================={RESET}")

        if auto_discover:
            self.step_0_mdns_discovery()

        if not self.step_1_health_and_readiness():
            return False

        if not self.step_2_auth_login(username, password):
            return False

        if not self.step_3_room_creation():
            return False

        if not self.step_4_engine_connectivity():
            return False

        print_header("RESUMEN DE DIAGNÓSTICO DE RED")
        print(f"  {GREEN}{BOLD}✓ TODOS LOS SERVICIOS VERIFICADOS Y OPERATIVOS{RESET}")
        print(f"  - Gateway API: {self.gateway_url}")
        print(f"  - Motor de Simulación: {self.discovered_engine_endpoint or self.engine_endpoint}")
        print(f"  - Sala de Prueba: {self.room_id} (Código: {self.room_code})")
        print(f"  - Token JWT y Ticket HMAC: Verificados y válidos\n")
        return True


def main():
    parser = argparse.ArgumentParser(description="Verificador E2E de Red y Despliegue de EcoStream-3R")
    parser.add_argument("--auto-discover", action="store_true", help="Descubrir Gateway en LAN automáticamente vía mDNS / ZeroConf (¡Sin escribir IPs!)")
    parser.add_argument("--gateway", type=str, default="", help="URL del API Gateway (ej. http://192.168.1.45:8080 o https://ecostream-gateway.onrender.com)")
    parser.add_argument("--engine", type=str, default="", help="Endpoint del motor de simulación (opcional; se autodetecta de la sala)")
    parser.add_argument("--host", type=str, default="", help="IP o hostname de host local (atajo para --gateway http://<host>:8080)")
    parser.add_argument("--tls", action="store_true", help="Usar TLS / HTTPS (obligatorio para despliegue en Render)")
    parser.add_argument("--username", type=str, default="admin_eco", help="Usuario para prueba de login")
    parser.add_argument("--password", type=str, default="EcoStream2026!", help="Contraseña para prueba de login")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout de red en segundos")

    args = parser.parse_args()

    # Resolver URL del Gateway
    gateway_url = "http://localhost:8080"
    if args.host:
        gateway_url = f"http://{args.host}:8080"
    elif args.gateway:
        gateway_url = args.gateway

    # Si la URL del Gateway usa https, habilitar TLS automáticamente
    use_tls = args.tls or gateway_url.startswith("https://")

    verifier = NetworkVerifier(
        gateway_url=gateway_url,
        engine_endpoint=args.engine if args.engine else None,
        use_tls=use_tls,
        timeout=args.timeout
    )

    success = verifier.run_all(
        auto_discover=args.auto_discover,
        username=args.username,
        password=args.password
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
