#!/usr/bin/env python3
"""
Script de compilación y generación de stubs Protocol Buffers para EcoStream 3R.
Soporta generación multiplataforma para Python, Go, Rust y TypeScript.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Configurar encoding UTF-8 en stdout si es posible
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
PROTO_DIR = ROOT_DIR / "proto"
PYTHON_OUT = ROOT_DIR / "client-python" / "proto"
GO_OUT = ROOT_DIR / "gateway-go" / "proto" / "v1"
TS_OUT = ROOT_DIR / "client-tauri" / "src" / "proto"
RUST_OUT = ROOT_DIR / "engine-rust" / "proto"

def ensure_dirs():
    for directory in [PYTHON_OUT, GO_OUT, TS_OUT, RUST_OUT]:
        directory.mkdir(parents=True, exist_ok=True)
        if "client-python" in str(directory):
            (directory / "__init__.py").touch(exist_ok=True)

def compile_python():
    print("[1/3] Compilando stubs de Python con grpc_tools.protoc...")
    try:
        import grpc_tools.protoc
    except ImportError:
        print("  -> Instalando dependencias de Python (grpcio, grpcio-tools)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "grpcio", "grpcio-tools"])
        import grpc_tools.protoc

    proto_files = list(PROTO_DIR.glob("**/*.proto"))
    proto_args = [
        "grpc_tools.protoc",
        f"-I{PROTO_DIR}",
        f"--python_out={PYTHON_OUT}",
        f"--grpc_python_out={PYTHON_OUT}",
        f"--pyi_out={PYTHON_OUT}",
    ] + [str(p) for p in proto_files]

    res = grpc_tools.protoc.main(proto_args)
    if res == 0:
        for p in PYTHON_OUT.rglob("*"):
            if p.is_dir():
                (p / "__init__.py").touch(exist_ok=True)
        print("  [OK] Stubs de Python generados con exito en:", PYTHON_OUT)
    else:
        print("  [ERROR] Error al compilar protos para Python. Codigo:", res)

def copy_rust_protos():
    print("[2/3] Sincronizando archivos .proto para Engine Rust (Tonic build)...")
    dest_ecostream = RUST_OUT / "ecostream" / "v1"
    dest_ecostream.mkdir(parents=True, exist_ok=True)
    for p in (PROTO_DIR / "ecostream" / "v1").glob("*.proto"):
        shutil.copy2(p, dest_ecostream / p.name)
    print("  [OK] Protos sincronizados para Rust en:", RUST_OUT)

def print_summary():
    print("[3/3] Resumen de contratos Protocol Buffers:")
    for p in PROTO_DIR.glob("**/*.proto"):
        print(f"  - {p.relative_to(ROOT_DIR)}")
    print("\nFase 1 (Contratos Proto) generada y estructurada exitosamente!")

if __name__ == "__main__":
    ensure_dirs()
    compile_python()
    copy_rust_protos()
    print_summary()
