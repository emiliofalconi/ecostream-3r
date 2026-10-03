# EcoStream 3R - AquaGuardians 💧🌱

> **Cátedra:** Computación en la Nube  
> **Institución:** Universidad Católica Andrés Bello (UCAB) - Escuela de Ingeniería en Informática  
> **Estado:** Fases 0 a 5 Completadas al 100% (Infraestructura, Gateway Go, Motor Rust 20Hz, Clientes Pygame & Web/Tauri)  

---

## 📖 Descripción General del Proyecto

**EcoStream 3R** es una plataforma de videojuego distribuido multijugador en tiempo real enfocado en la concientización y preservación del recurso hídrico a través del paradigma de las **3R (Reducir, Reusar y Reciclar)**:

1. **Reducir (Reduce):** Localización y reparación urgente de fugas y roturas a alta presión en tuberías de agua potable comunales antes de que el embalse se agote.
2. **Reusar (Reuse):** Operación de válvulas y compuertas de desvío para canalizar aguas grises hacia parcelas de cultivo y huertos comunitarios, reduciendo el consumo de agua potable.
3. **Reciclar (Recycle):** Operación de una planta de filtrado ecológico (carbón activo y grava) para descontaminar aguas residuales y reintegrar agua pura al embalse central.

El juego incluye además un sistema de **telemetría de latencia RTT Ping-Pong continua**, **chat multijugador en tiempo real** y un **modo Bot autónomo con IA** para pruebas de carga y evaluación de la cátedra.

---

## 🛠️ Pila Tecnológica Asignada

| Capa | Tecnología | Justificación y Responsabilidad |
| :--- | :--- | :--- |
| **Persistencia** | **PostgreSQL 16** | Modelo relacional para cuentas de usuario, historial de partidas, métricas y consistencia transaccional ACID. |
| **Control Plane & Gateway** | **Go 1.22+** | Autenticación JWT, Matchmaking, Worker Pools con **Goroutines**, endpoints de salud (`/healthz`, `/readyz`), documentación OpenAPI/Swagger interactiva y disyuntores (*Circuit Breakers* con `sony/gobreaker`). |
| **Data Plane & Simulación** | **Rust (Tokio / Tonic)** | Bucle de simulación física autoritativo a **20 Ticks/segundo**, gestión de memoria libre de Garbage Collector y streaming bidireccional gRPC de ultra-baja latencia (1-2 ms). |
| **Cliente 1 (Web / Desktop)** | **Tauri / Web (TypeScript + Canvas 2D + Vite)** | Interfaz gráfica moderna con estética Cyber-Eco, ondas sinusoidales, partículas de soldadura/agua, Web Audio procedural y conexión en vivo. |
| **Cliente 2 (Multiplataforma / Bot)** | **Python (Pygame-CE + grpcio)** | Cliente interactivo con teclado (`WASD`, `Espacio`, `R`, `F`), telemetría RTT en vivo y flag `--bot` para stress testing y evaluación automática. |
| **Comunicación Inter-Servicios** | **gRPC & Protocol Buffers (proto3)** | Serialización binaria tipada estricta, streaming reactivo y telemetría de latencia en vivo (RTT Ping-Pong). |

---

## ☁️ Patrones Nativos de la Nube (Cloud-Native)

El sistema incorpora los siguientes patrones canónicos de arquitectura en la nube:
1. **API Gateway Pattern:** Centralización de entrada para clientes (`:8080` REST / `:50051` gRPC), abstrayendo la topología interna de workers y persistencia.
2. **Circuit Breaker (Disyuntor):** Prevención de fallos en cascada ante caídas transitorias de PostgreSQL (`PostgreSQL-Breaker`) o workers de Rust (`Rust-Engine-Breaker`).
3. **Health Endpoint Monitoring:** Cumplimiento de estándares de sondeo de vitalidad y disponibilidad (`grpc.health.v1.Health` y `/healthz`, `/readyz`).
4. **Authoritative Server Pattern:** Eliminación de trampas y desincronizaciones calculando el estado físico del mundo enteramente en Rust a 20 Hz.
5. **Cache-Aside / Materialized State:** Desacoplamiento entre memoria volátil de lobbies rápidos y persistencia en disco de PostgreSQL.
6. **Zero-SPOF & Redundant Gateways:** Arquitectura diseñada con IP Virtual flotante (Keepalived) y balanceo Client-Side.

---

## 🚀 Despliegue Rápido y Ejecución Local

Con Docker Desktop abierto:

```powershell
# 1. Levantar toda la infraestructura y servicios en Docker
docker compose -f deployments/docker-compose.yml up -d --build

# 2. Probar Cliente Python Interactivo (Modo Humano):
python client-python/main_game.py

# 3. Probar Cliente Python en Modo Bot Autónomo (Pruebas de Estrés):
python client-python/main_game.py --bot

# 4. Probar Cliente Web / Tauri (TypeScript + Canvas 2D):
cd client-tauri
npm run dev
# Abre http://localhost:5173 en tu navegador
```

---

## 📚 Documentación Técnica Detallada

Para consultar la planificación técnica exhaustiva y el estado de avance, visita el directorio `docs/`:
- [docs/GUIA_DESPLIEGUE_Y_TESTS.md](docs/GUIA_DESPLIEGUE_Y_TESTS.md): 🛠️ **Catálogo de scripts, guía de despliegue de pruebas y pasos para continuar.**
- [docs/AVANCES_PROYECTO.md](docs/AVANCES_PROYECTO.md): 📊 **Bitácora de avances, tablero de tareas completadas y seguimiento del plan.**
- [docs/ARQUITECTURA_Y_PLANIFICACION.md](docs/ARQUITECTURA_Y_PLANIFICACION.md): Documento integral de infraestructura, tolerancia a fallos Zero-SPOF, concurrencia en Go con Goroutines, seguridad mTLS/JWT y despliegue (LAN vs Nube).
- [docs/DISENO_DEL_JUEGO.md](docs/DISENO_DEL_JUEGO.md): Documento de diseño de mecánicas, balance hídrico, eventos climáticos y contratos gRPC.
- [docs/ARQUITECTURA_FLUJOS_Y_UML.md](docs/ARQUITECTURA_FLUJOS_Y_UML.md): Especificación detallada de flujos, balanceo de carga, detección de fallos y diagramas UML.
- [docs/PROMPTS_DISENO_SPRITES.md](docs/PROMPTS_DISENO_SPRITES.md): Guía de prompts para generación de arte y tilesets Pixel Art Top-Down.

---

## 🗺️ Hoja de Ruta de Desarrollo

- [x] **Fase 0: Planificación y Arquitectura de Nube**
  - [x] Definición conceptual de las 3R para preservación de agua.
  - [x] Selección e integración de tecnologías (Postgres, Go, Rust, TypeScript/Tauri, Python).
  - [x] Estrategia de tolerancia a fallos y eliminación de SPOF en el Gateway.
  - [x] Justificación técnica de Goroutines y selección de los patrones cloud-native.
  - [x] Especificación de estrategia de gRPC nativo HTTP/2 en Tauri.
  - [x] Definición de protocolo de reconexión transitoria ante microcortes de red (`reconnect_ticket`).
  - [x] Generación de guía de prompts y sprites Pixel Art 2D (`docs/PROMPTS_DISENO_SPRITES.md`).
- [x] **Fase 1: Contratos de Comunicación (Protocol Buffers)**
  - [x] Creación de `proto/ecostream/v1/common.proto`, `auth.proto`, `matchmaking.proto` y `gameplay.proto`.
  - [x] Automatización de toolchain Protobuf con compilador unificado multi-lenguaje (`scripts/build_protos.py`).
  - [x] Generación automática de stubs para Go, Rust, TS y Python.
  - [x] Generación de especificación Swagger/OpenAPI v3 (`docs/swagger/openapi.json`).
- [x] **Fase 2: Infraestructura y Base de Datos**
  - [x] `deployments/docker-compose.yml` con PostgreSQL 16 y pgAdmin 4.
  - [x] Script DDL `deployments/postgres/schema.sql` (tablas: `users`, `rooms`, `room_players`, `matches`, `audit_logs`).
  - [x] Estructura de tablas para asignación stateless de salas y workers.
  - [x] Configuración de variables de entorno `.env.example`.
- [x] **Fase 3: Implementación del Gateway y Orquestador (Go)**
  - [x] Endpoints de autenticación JWT y registro en Postgres.
  - [x] Matchmaking y coordinación de salas stateless.
  - [x] Worker pools con Goroutines y servidores de salud HTTP/gRPC (`/healthz`, `/readyz`).
  - [x] Circuit Breakers (`sony/gobreaker`) hacia PostgreSQL y motor Rust.
  - [x] Swagger UI incrustado interactivo (`http://localhost:8080/swagger/`).
- [x] **Fase 4: Motor de Simulación en Tiempo Real (Rust)**
  - [x] Servidor Tonic gRPC con streaming bidireccional a 20 Hz (`engine-rust:50052`).
  - [x] Lógica autoritativa de balance hídrico (reserva comunal, roturas dinámicas, pureza).
  - [x] Acciones 3R (1. Reducir fugas, 2. Reusar aguas grises, 3. Reciclar en planta biológica).
  - [x] Buffer de reconciliación y tickets de reconexión rápida (`reconnect_ticket`).
  - [x] Telemetría de latencia RTT Ping-Pong en vivo.
- [x] **Fase 5: Clientes Multiplataforma (Tauri / Web y Python)**
  - [x] Cliente Web / Tauri (TypeScript + Vite + Canvas 2D) con animaciones de fluidos, partículas, HUD glassmorphism y sintetizador de sonido Web Audio procedural.
  - [x] Cliente interactivo Pygame en Python con soporte de flag `--bot` para stress testing autónomo y telemetría RTT.
- [ ] **Fase 6: Despliegue en Nube, Pruebas de Carga y Evaluación Final**
  - [ ] Pruebas de carga masiva concurrente con bots.
  - [ ] Pruebas de conmutación por error (Chaos Testing / desconexión forzada de componentes).
