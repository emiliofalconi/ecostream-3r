#!/usr/bin/env bash
# ==============================================================================
# EcoStream-3R — Script de Gestión de Servidores Locales
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/deployments/docker-compose.yml"
ENV_FILE="$PROJECT_ROOT/deployments/.env"

# Colores para la consola
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

echo -e "${BOLD}${CYAN}===================================================================${RESET}"
echo -e "${BOLD}${CYAN}  EcoStream-3R: Gestor de Servidores Locales (Edge / LAN)          ${RESET}"
echo -e "${BOLD}${CYAN}===================================================================${RESET}"

# Verificar si Docker está corriendo
if ! docker info >/dev/null 2>&1; then
    echo -e "${YELLOW}[AVISO] El demonio de Docker no está activo actualmente.${RESET}"
    echo -e "Puedes iniciarlo con: ${BOLD}sudo systemctl start docker${RESET}"
    echo ""
    read -rp "¿Deseas intentar arrancar Docker ahora con sudo? (s/N): " start_docker
    if [[ "$start_docker" =~ ^[sSyY]$ ]]; then
        sudo systemctl start docker
    else
        echo -e "${RED}[ERROR] Se requiere Docker activo para arrancar los servicios en contenedores.${RESET}"
        exit 1
    fi
fi

echo -e "\nSelecciona una opción:"
echo -e "  ${BOLD}1)${RESET} Arrancar TODO en Docker (PostgreSQL, Redis, Gateway Go y Motor Rust)"
echo -e "  ${BOLD}2)${RESET} Arrancar solo Bases de Datos (PostgreSQL + Redis en Docker para desarrollo nativo)"
echo -e "  ${BOLD}3)${RESET} Ver logs en tiempo real (docker compose logs -f)"
echo -e "  ${BOLD}4)${RESET} Ver estado de los servicios (docker compose ps)"
echo -e "  ${BOLD}5)${RESET} Detener y apagar todos los servidores locales"
echo -e "  ${BOLD}0)${RESET} Salir"
echo ""

read -rp "Opción [1-5]: " opt

case "$opt" in
    1)
        echo -e "\n${GREEN}[INFO] Levantando toda la infraestructura local con Docker Compose...${RESET}"
        docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d
        echo -e "\n${BOLD}${GREEN}✓ Servidores locales activos:${RESET}"
        echo -e "  - Gateway HTTP : http://localhost:8080"
        echo -e "  - Gateway gRPC : localhost:50051"
        echo -e "  - Motor Rust   : localhost:50052 (Data Plane 20 Hz)"
        echo -e "  - PostgreSQL   : localhost:5432"
        echo -e "  - Redis Cache  : localhost:6379"
        echo -e "  - Anuncio mDNS : _ecostream._tcp.local. (LAN)"
        echo -e "\nPrueba tus clientes ejecutando:"
        echo -e "  ${CYAN}python3 client-python/bot.py${RESET}"
        ;;
    2)
        echo -e "\n${GREEN}[INFO] Levantando PostgreSQL y Redis en Docker...${RESET}"
        docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d postgres redis
        echo -e "\n${BOLD}${GREEN}✓ Bases de datos listas en local (5432 y 6379).${RESET}"
        echo -e "Ahora puedes arrancar en terminales separadas:"
        echo -e "  1. Gateway: ${CYAN}cd gateway-go && go run cmd/server/main.go${RESET}"
        echo -e "  2. Motor:   ${CYAN}CARGO_TARGET_DIR=/tmp/target_engine cargo run --manifest-path engine-rust/Cargo.toml${RESET}"
        ;;
    3)
        echo -e "\n${CYAN}[INFO] Mostrando logs (Ctrl+C para salir)...${RESET}"
        docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs -f
        ;;
    4)
        docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
        ;;
    5)
        echo -e "\n${YELLOW}[INFO] Deteniendo servidores locales...${RESET}"
        docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down
        echo -e "${GREEN}✓ Servidores detenidos.${RESET}"
        ;;
    0)
        echo "Saliendo..."
        exit 0
        ;;
    *)
        echo -e "${RED}Opción inválida.${RESET}"
        exit 1
        ;;
esac
