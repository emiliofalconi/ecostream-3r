#!/usr/bin/env bash
# ==============================================================================
# EcoStream 3R - Lanzador del Cliente Pygame (client-python)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

VENV_PATH="/home/stalinft/.cache/ecostream_venv"
if [ ! -d "${VENV_PATH}" ]; then
    if [ -d "${ROOT_DIR}/.venv" ]; then
        VENV_PATH="${ROOT_DIR}/.venv"
    else
        echo "[SETUP] Creando entorno virtual en ${ROOT_DIR}/.venv..."
        python3 -m venv "${ROOT_DIR}/.venv"
        VENV_PATH="${ROOT_DIR}/.venv"
        "${VENV_PATH}/bin/pip" install -r "${ROOT_DIR}/requirements.txt"
    fi
fi

PYTHON_BIN="${VENV_PATH}/bin/python3"

echo "======================================================================"
echo "  💧 EcoStream 3R - AquaGuardians (Cliente Gráfico Pygame-CE)        "
echo "======================================================================"
echo "  Python binary: ${PYTHON_BIN}"
echo "  Argumentos: $*"
echo "----------------------------------------------------------------------"

exec "${PYTHON_BIN}" "${ROOT_DIR}/client-python/main_game.py" "$@"
