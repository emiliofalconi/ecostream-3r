#!/usr/bin/env python3
"""
EcoStream-3R — Módulo de Descubrimiento de Servidores (Edge-First Auto-Discovery)
---------------------------------------------------------------------------------
Implementa la estrategia de conexión inteligente:
1. Intenta descubrir servidores locales vía Multicast DNS (mDNS / ZeroConf) '_ecostream._tcp.local.'.
2. Si mDNS no responde o zeroconf no está disponible, realiza un sondeo HTTP ultrarrápido a localhost:8080/healthz.
3. Si los servidores locales están disponibles, los selecciona como prioritarios (Baja Latencia / LAN).
4. Si ningún servidor local responde, conmuta automáticamente a la infraestructura en la nube en Render.com.
"""

import sys
import time
import socket
import urllib.request
import urllib.error
from typing import Tuple, Dict, Any, Optional

# Configuración de Servidores en la Nube (Render.com)
CLOUD_GATEWAY_URL = "https://ecostream-gateway.onrender.com"
CLOUD_ENGINE_ENDPOINT = "ecostream-engine.onrender.com:443"

# Configuración por defecto para Servidores Locales
DEFAULT_LOCAL_GATEWAY_URL = "http://localhost:8080"
DEFAULT_LOCAL_ENGINE_ENDPOINT = "localhost:50052"
MDNS_SERVICE_TYPE = "_ecostream._tcp.local."


def probe_http_health(url: str, timeout: float = 0.5) -> bool:
    """Verifica si un endpoint HTTP responde rápidamente con status 200 OK."""
    probe_url = f"{url.rstrip('/')}/healthz"
    try:
        req = urllib.request.Request(probe_url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def discover_via_mdns(timeout: float = 1.8) -> Optional[Dict[str, Any]]:
    """Busca el servicio mDNS '_ecostream._tcp.local.' en la red local."""
    try:
        from zeroconf import Zeroconf, ServiceBrowser, ServiceListener
    except ImportError:
        return None

    class EcoStreamListener(ServiceListener):
        def __init__(self):
            self.found_info: Optional[Dict[str, Any]] = None

        def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            info = zc.get_service_info(type_, name)
            if info:
                # Extraer dirección IP
                addresses = info.parsed_scoped_addresses()
                ip = addresses[0] if addresses else "127.0.0.1"

                # Extraer propiedades del TXT record
                props = {k.decode("utf-8", "ignore"): v.decode("utf-8", "ignore")
                         for k, v in info.properties.items()}
                gateway_port = int(props.get("gateway_port", info.port or 8080))
                engine_port = int(props.get("engine_port", 50052))

                self.found_info = {
                    "ip": ip,
                    "gateway_port": gateway_port,
                    "engine_port": engine_port,
                    "name": name,
                    "properties": props
                }

        def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            pass

        def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            pass

    zc = None
    try:
        zc = Zeroconf()
        listener = EcoStreamListener()
        browser = ServiceBrowser(zc, MDNS_SERVICE_TYPE, listener)

        start = time.time()
        while time.time() - start < timeout:
            if listener.found_info:
                break
            time.sleep(0.1)

        browser.cancel()
        return listener.found_info
    except Exception:
        return None
    finally:
        if zc:
            try:
                zc.close()
            except Exception:
                pass


def discover_servers(prefer_local: bool = True,
                     mdns_timeout: float = 1.8,
                     probe_timeout: float = 0.5) -> Tuple[str, str, str]:
    """
    Descubre el Gateway y Engine a utilizar.
    Retorna una tupla: (gateway_url, engine_endpoint, source_mode)
    donde source_mode es 'LOCAL_MDNS', 'LOCAL_PROBE' o 'CLOUD_RENDER'.
    """
    if prefer_local:
        # 1. Intentar descubrimiento mDNS
        mdns_result = discover_via_mdns(timeout=mdns_timeout)
        if mdns_result:
            ip = mdns_result["ip"]
            gw_port = mdns_result["gateway_port"]
            eng_port = mdns_result["engine_port"]
            gw_url = f"http://{ip}:{gw_port}"
            eng_ep = f"{ip}:{eng_port}"
            # Verificar salud básica antes de confirmar
            if probe_http_health(gw_url, timeout=0.8):
                return gw_url, eng_ep, "LOCAL_MDNS"

        # 2. Intento directo por sondeo local HTTP en localhost
        if probe_http_health(DEFAULT_LOCAL_GATEWAY_URL, timeout=probe_timeout):
            return DEFAULT_LOCAL_GATEWAY_URL, DEFAULT_LOCAL_ENGINE_ENDPOINT, "LOCAL_PROBE"

    # 3. Fallback automático a los servidores en la nube en Render.com
    return CLOUD_GATEWAY_URL, CLOUD_ENGINE_ENDPOINT, "CLOUD_RENDER"


if __name__ == "__main__":
    print("===================================================================")
    print("  EcoStream-3R — Diagnóstico de Descubrimiento (Auto-Discovery)    ")
    print("===================================================================")
    print("Iniciando sondeo de servidores (Edge mDNS -> Local HTTP -> Cloud Render)...")

    gw, eng, mode = discover_servers(prefer_local=True)
    print(f"\nResultado de Descubrimiento:")
    print(f"  Modo Seleccionado : {mode}")
    print(f"  Gateway URL       : {gw}")
    print(f"  Engine Endpoint   : {eng}")

    if mode == "LOCAL_MDNS":
        print("\n  [OK] Conectado a Servidor Local anunciado por mDNS (ZeroConf en LAN).")
    elif mode == "LOCAL_PROBE":
        print("\n  [OK] Conectado a Servidor Local en localhost (Sondeo HTTP activo).")
    else:
        print("\n  [INFO] Servidor local no detectado. Conectado a la Nube (Render.com).")
