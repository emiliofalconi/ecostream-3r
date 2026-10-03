# EcoStream 3R - AquaGuardians 💧🌱

> **Cátedra:** Computación en la Nube  
> **Institución:** Universidad Católica Andrés Bello (UCAB) - Escuela de Ingeniería en Informática  
> **Estado:** Fase de Planificación, Diseño Arquitectural y Prototipado de Assets  

---

## 📖 Descripción General del Proyecto

**EcoStream 3R** es una plataforma de videojuego distribuido multijugador en tiempo real enfocado en la concientización y preservación del recurso hídrico a través del paradigma de las **3R (Reducir, Reusar y Reciclar)**:

1. **Reducir (Reduce):** Localización y reparación urgente de fugas y roturas a alta presión en tuberías de agua potable comunales antes de que el embalse se agote.
2. **Reusar (Reuse):** Operación de válvulas y compuertas de desvío para canalizar aguas grises hacia parcelas de cultivo y huertos comunitarios, reduciendo el consumo de agua potable.
3. **Reciclar (Recycle):** Operación de una planta de filtrado ecológico (carbón activo y grava) para descontaminar aguas residuales y reintegrar agua pura al embalse central.

El juego incluye además un sistema de **chat multijugador en tiempo real** integrado para la coordinación y comunicación entre los participantes de la partida.

---

## 🛠️ Pila Tecnológica Asignada

| Capa | Tecnología | Justificación y Responsabilidad |
| :--- | :--- | :--- |
| **Persistencia** | **PostgreSQL 16** | Modelo relacional para cuentas de usuario, historial de partidas, métricas y consistencia transaccional ACID. |
| **Control Plane & Gateway** | **Go 1.22+** | Autenticación JWT, Matchmaking, Worker Pools con **Goroutines**, endpoints de salud (`/healthz`, `/readyz`), documentación OpenAPI/Swagger interactiva y disyuntores (*Circuit Breakers*). |
| **Data Plane & Simulación** | **Rust (Tokio / Tonic)** | Bucle de simulación física autoritativo a **20 Ticks/segundo**, gestión de memoria libre de Garbage Collector y streaming bidireccional gRPC de ultra-baja latencia. |
| **Cliente 1 (Escritorio / UI)** | **Tauri (TypeScript + Vite)** | Interfaz gráfica de escritorio con estética Pixel Art 2D sobre Canvas y conexión directa gRPC HTTP/2 nativa sin sobrecarga de proxies. |
| **Cliente 2 (Multiplataforma / Bot)** | **Python (Pygame + grpcio)** | Cliente interactivo con teclado para compañeros/evaluadores, con opción de activar modo `--bot` para pruebas de estrés y escalabilidad en la nube. |
| **Comunicación Inter-Servicios** | **gRPC & Protocol Buffers (proto3)** | Serialización binaria tipada estricta, streaming reactivo y telemetría de latencia en vivo (RTT Ping-Pong). |

---

## ☁️ Patrones Nativos de la Nube (Cloud-Native)

El sistema incorpora al menos 5 patrones canónicos de arquitectura en la nube:
1. **API Gateway Pattern:** Centralización de entrada para clientes, abstrayendo la topología interna de workers y persistencia.
2. **Circuit Breaker (Disyuntor):** Prevención de fallos en cascada ante caídas transitorias de PostgreSQL o workers de Rust.
3. **Health Endpoint Monitoring:** Cumplimiento de estándares de sondeo de vitalidad y disponibilidad (`grpc.health.v1.Health` y `/healthz`, `/readyz`).
4. **Authoritative Server Pattern:** Eliminación de trampas y desincronizaciones calculando el estado del mundo enteramente en Rust.
5. **Cache-Aside / Materialized State:** Desacoplamiento entre memoria volátil de lobbies rápidos y persistencia en disco de PostgreSQL.

---

## 🎨 Apartado Visual y Especificaciones de Sprites

El apartado visual del juego sigue una dirección de arte en **Pixel Art 2D en vista top-down 3/4**, orientada a la gestión clara y visual del agua y los recursos ecológicos.

Se ha elaborado una guía completa con **prompts optimizados para modelos de generación de arte por IA** (Midjourney, DALL-E 3, Stable Diffusion, etc.) para crear cada uno de los componentes visuales:
- Terrenos modulares (pasto, tierra, caminos, orillas de estanque).
- Mecánica **Reducir** (aspersores, canales con flujo y roturas con fugas animadas).
- Mecánica **Reusar** (desvíos de aguas grises y huertos agrícolas floreciendo).
- Mecánica **Reciclar** (molino de agua rural y lechos biológicos de purificación).
- Avatares de jugadores con overoles y herramientas para partidas multijugador.

👉 **Consulta la guía de prompts aquí:** [docs/PROMPTS_DISENO_SPRITES.md](docs/PROMPTS_DISENO_SPRITES.md)

---

## 📚 Documentación Técnica Detallada

Para consultar la planificación técnica exhaustiva y el estado de avance, visita el directorio `docs/`:
- [docs/GUIA_DESPLIEGUE_Y_TESTS.md](docs/GUIA_DESPLIEGUE_Y_TESTS.md): 🛠️ **Catálogo de scripts, guía de despliegue de pruebas y pasos para continuar.**
- [docs/AVANCES_PROYECTO.md](docs/AVANCES_PROYECTO.md): 📊 **Bitácora de avances, tablero de tareas completadas y seguimiento del plan.**
- [docs/ARQUITECTURA_Y_PLANIFICACION.md](docs/ARQUITECTURA_Y_PLANIFICACION.md): Documento integral de infraestructura, tolerancia a fallos Zero-SPOF, concurrencia en Go con Goroutines, seguridad mTLS/JWT y despliegue (LAN vs Nube).
- [docs/DISENO_DEL_JUEGO.md](docs/DISENO_DEL_JUEGO.md): Documento de diseño de mecánicas, balance hídrico, eventos climáticos y contratos gRPC preliminares.
- [docs/ARQUITECTURA_FLUJOS_Y_UML.md](docs/ARQUITECTURA_FLUJOS_Y_UML.md): Especificación detallada de flujos, balanceo de carga, detección de fallos y guía exhaustiva de diagramas UML.

---

## 🚀 Hoja de Ruta de Desarrollo

- [x] **Fase 0: Planificación y Arquitectura de Nube**
  - [x] Definición conceptual de las 3R para preservación de agua.
  - [x] Selección e integración de tecnologías (Postgres, Go, Rust, TypeScript/Tauri, Python).
  - [x] Estrategia de tolerancia a fallos y eliminación de SPOF en el Gateway.
  - [x] Justificación técnica de Goroutines y selección de los 5 patrones cloud-native.
  - [x] Especificación de estrategia de gRPC nativo HTTP/2 en Tauri (agregado por Victor).
  - [x] Definición de protocolo de reconexión transitoria ante microcortes de red (agregado por Victor).
  - [ ] Generación y consolidación de assets y tileset Pixel Art 2D.
- [x] **Fase 1: Contratos de Comunicación (Protocol Buffers)**
  - [x] Creación de `proto/ecostream/v1/common.proto`, `auth.proto`, `matchmaking.proto` y `gameplay.proto`.
  - [x] Automatización de toolchain Protobuf con `buf` o script unificado multi-lenguaje (Go, Rust, TS, Python) (agregado por Victor).
  - [x] Generación automática de stubs para Go, Rust, TS y Python.
  - [x] Generación de especificación Swagger/OpenAPI v3 (`docs/swagger/openapi.json`).
- [x] **Fase 2: Infraestructura y Base de Datos**
  - [x] `deployments/docker-compose.yml` con PostgreSQL 16 y pgAdmin 4.
  - [x] Script DDL `deployments/postgres/schema.sql` (tablas: `users`, `rooms`, `matches`, `audit_logs`).
  - [x] Estructura de tablas para asignación stateless de salas y workers (agregado por Victor).
  - [x] Configuración de variables de entorno `.env.example`.
- [x] **Fase 3: Implementación del Gateway y Orquestador (Go)**
  - [x] Endpoints de autenticación, matchmaking y registro en Postgres.
  - [x] Coordinación de salas stateless sobre Postgres/Redis para cluster redundante (agregado por Victor).
  - [x] Worker pools con Goroutines y servidores de salud HTTP/gRPC (`/healthz`, `/readyz`).
  - [x] Circuit Breakers (`sony/gobreaker`) hacia PostgreSQL y motor Rust.
  - [x] Swagger UI incrustado interactivo (`http://localhost:8080/swagger/`).
- [x] **Fase 4: Motor de Simulación en Tiempo Real (Rust)**
  - [x] Servidor Tonic gRPC con streaming bidireccional a 20 Hz (`engine-rust:50052`).
  - [x] Lógica autoritativa de balance hídrico (reserva comunal, roturas dinámicas, pureza).
  - [x] Acciones 3R (1. Reducir fugas, 2. Reusar aguas grises, 3. Reciclar en planta biológica).
  - [x] Buffer de reconciliación y tickets de reconexión rápida (`reconnect_ticket`) (agregado por Victor).
  - [x] Telemetría de latencia RTT Ping-Pong en vivo.
- [ ] **Fase 5: Clientes Multiplataforma (Tauri y Python)**
  - [ ] Cliente interactivo Tauri + Vite + TypeScript con Canvas 2D y gRPC nativo (agregado por Victor).
  - [ ] Cliente interactivo Pygame en Python con soporte de flag `--bot` para stress testing.
