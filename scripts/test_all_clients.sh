#!/usr/bin/env bash
# ==============================================================================
# EcoStream 3R - Suite de Validación de Clientes (Tauri + Python)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

VENV_PATH="/home/stalinft/.cache/ecostream_venv"
if [ ! -d "${VENV_PATH}" ]; then
    VENV_PATH="${ROOT_DIR}/.venv"
fi
PYTHON_BIN="${VENV_PATH}/bin/python3"

echo "======================================================================"
echo "  [TEST 1/3] Validación de Contratos Protobuf y OpenAPI (Python)     "
echo "======================================================================"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/test_contracts.py"

echo ""
echo "======================================================================"
echo "  [TEST 2/3] Compilación y Tipado TypeScript (client-tauri)          "
echo "======================================================================"
npm --prefix "${ROOT_DIR}/client-tauri" run build

echo ""
echo "======================================================================"
echo "  [TEST 3/3] Prueba de Carga Bot 20 Hz contra Render Cloud           "
echo "======================================================================"
"${PYTHON_BIN}" "${ROOT_DIR}/client-python/bot.py" --env cloud --duration 3

echo ""
echo "======================================================================"
echo "  🎉 TODAS LAS VALIDACIONES DE CLIENTES PASARON CON ÉXITO (100% OK)  "
echo "======================================================================"
