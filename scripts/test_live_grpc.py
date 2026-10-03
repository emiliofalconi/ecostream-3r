#!/usr/bin/env python3
"""
Prueba de integración en vivo: Levanta el servidor gRPC mock y corre el cliente interactivo.
"""

import sys
import time
from pathlib import Path

# Añadir carpetas al path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "client-python"))
sys.path.insert(0, str(ROOT_DIR / "client-python" / "proto"))

from mock_server import serve
from test_client import run_interactive_client

def main():
    print("[INTEGRACION] Iniciando servidor gRPC en background...")
    server = serve(port=50051)
    time.sleep(0.5)

    try:
        run_interactive_client(host="localhost:50051")
    finally:
        server.stop(0)
        print("[INTEGRACION] Servidor gRPC finalizado.")

if __name__ == "__main__":
    main()
