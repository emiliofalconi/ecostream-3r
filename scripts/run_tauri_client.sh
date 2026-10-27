#!/usr/bin/env bash
# ==============================================================================
# EcoStream 3R - Lanzador del Cliente Web/Tauri
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CLIENT_DIR="${ROOT_DIR}/client-tauri"

echo "======================================================================"
echo "  💧 EcoStream 3R - AquaGuardians (Cliente Web / Desktop)            "
echo "======================================================================"

if [ ! -d "${CLIENT_DIR}/node_modules" ]; then
    echo "[SETUP] Instalando dependencias en ${CLIENT_DIR}..."
    npm --prefix "${CLIENT_DIR}" install --no-bin-links
fi

echo "[START] Iniciando servidor Vite en http://localhost:5173 ..."
echo "        Presiona Ctrl+C para detener el servidor."
echo "----------------------------------------------------------------------"

cd "${CLIENT_DIR}"
npm run dev -- --host 0.0.0.0 --port 5173
