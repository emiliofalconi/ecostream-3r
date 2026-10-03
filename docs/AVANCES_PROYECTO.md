# 📊 Bitácora de Avances y Seguimiento: EcoStream 3R

> **Proyecto:** EcoStream 3R - AquaGuardians 💧🌱  
> **Cátedra:** Computación en la Nube (UCAB)  
> **Rama Actual:** `fase1`  
> **Última Actualización:** Octubre 2026  

---

## 📈 Tablero General del Plan de Trabajo

| Fase | Descripción | Estado | Progreso |
| :---: | :--- | :---: | :---: |
| **Fase 0** | Planificación, Arquitectura Zero-SPOF y Diseño del Juego | ✅ **Completada** | 100% |
| **Fase 1** | Contratos de Comunicación (gRPC / Protocol Buffers & OpenAPI) | ✅ **Completada** | 100% |
| **Fase 2** | Infraestructura y Base de Datos (Docker & PostgreSQL 16) | ✅ **Completada** | 100% |
| **Fase 3** | Control Plane & Gateway Orquestador (Go 1.22+) | ✅ **Completada** | 100% |
| **Fase 4** | Motor de Simulación Autoritativa a 20 Hz (Rust Tokio/Tonic) | ⏳ **Siguiente** | 0% |
| **Fase 5** | Clientes de Juego (Tauri TS Canvas 2D & Python Bot/CLI) | ⏳ **Pendiente** | 0% |
| **Fase 6** | Despliegue en Nube, Pruebas de Carga y Evaluación Final | ⏳ **Pendiente** | 0% |

---

## 🔍 Detalle de Avance por Fase (Plan Original vs. Ejecución)

### ✅ Fase 0: Planificación y Arquitectura de Nube (Completada)
- [x] ~~**Definición conceptual de las 3R aplicadas al agua:**~~ (Reducir fugas, Reusar aguas grises en huertos, Reciclar aguas residuales en planta biológica).
- [x] ~~**Selección e integración del stack políglota:**~~ (Go + Rust + PostgreSQL + Tauri/TS + Python).
- [x] ~~**Estrategia de tolerancia a fallos Zero-SPOF:**~~ (Gateways redundantes con Keepalived/VIP, Cloud Load Balancer y Client-Side Load Balancing en gRPC).
- [x] ~~**Justificación de concurrencia y Goroutines:**~~ (Dispatcher asíncrono, worker pools, monitores de salud no bloqueantes).
- [x] ~~**Adopción de 5 patrones Cloud-Native:**~~ (API Gateway, Circuit Breaker, Health Probes, Authoritative Server, Cache-Aside/Stateless State).
- [x] ~~**Estrategia de gRPC nativo HTTP/2 en Tauri**~~ *(agregado por Victor)*.
- [x] ~~**Definición de protocolo de reconexión transitoria ante microcortes**~~ *(agregado por Victor)*.
- [x] ~~**Guía de prompts para generación de sprites Pixel Art Top-Down:**~~ (`docs/PROMPTS_DISENO_SPRITES.md`).

---

### ✅ Fase 1: Contratos de Comunicación y Protocol Buffers (Completada)
- [x] ~~**Definición de tipos base y telemetría común:**~~ (`proto/ecostream/v1/common.proto`).
  - Roles especializados (`PlayerRole`), coordenadas (`Vector2D`), métricas hídricas (`WaterMetrics`), mensajes `Ping`/`Pong` para telemetría RTT.
- [x] ~~**Definición del Servicio de Autenticación y Cuentas:**~~ (`proto/ecostream/v1/auth.proto`).
  - RPCs: `Register`, `Login`, `VerifyToken`, `GetProfile` con JWT claims.
- [x] ~~**Definición del Servicio de Matchmaking y Lobbies:**~~ (`proto/ecostream/v1/matchmaking.proto`).
  - RPCs: `CreateRoom`, `JoinRoom`, `QuickMatch`, `LeaveRoom`, `GetRoomStatus`, `StartMatch`, `ListAvailableRooms`.
  - Generación de `room_ticket` para enrutar clientes directamente a los workers de Rust.
- [x] ~~**Definición del Servicio de Simulación y Bucle Autoritativo a 20 Hz:**~~ (`proto/ecostream/v1/gameplay.proto`).
  - Stream bidireccional continuo `StreamGame` (Cliente $\leftrightarrow$ Rust Server).
  - Acciones de las 3R: `RepairPipeAction` (Reducir), `DivertValveAction` (Reusar), `OperateRecycleAction` (Reciclar).
  - Servicio de chat multijugador en tiempo real (`SendChatMessage`, `StreamChat`).
  - RPC `ReconnectSession` con margen de gracia de 5s y snapshot de reconciliación *(agregado por Victor)*.
- [x] ~~**Automatización del Toolchain Protobuf:**~~ (`proto/buf.yaml`, `proto/buf.gen.yaml` y script unificado `scripts/build_protos.py`) *(agregado por Victor)*.
- [x] ~~**Generación de stubs y tipos para Python:**~~ (`client-python/proto/ecostream/v1/`).
- [x] ~~**Sincronización de contratos para el motor Rust:**~~ (`engine-rust/proto/ecostream/v1/`).
- [x] ~~**Especificación OpenAPI 3.0 / Swagger JSON:**~~ (`docs/swagger/openapi.json`) para documentación interactiva de endpoints del Gateway.

---

### ⏳ Fase 2: Infraestructura y Base de Datos (Siguiente)
- [ ] Creación de `deployments/docker-compose.yml` (PostgreSQL 16, pgAdmin opcional, redes aisladas).
- [ ] Creación de scripts DDL `deployments/postgres/schema.sql` (tablas: `users`, `rooms`, `matches`, `eco_metrics`).
- [ ] Estructura de tablas y mutex para asignación de salas stateless entre múltiples Gateways Go *(agregado por Victor)*.
- [ ] Configuración de variables de entorno (`.env.example`).

---

### ⏳ Fase 3: Gateway y Orquestador en Go (Pendiente)
- [ ] Inicialización de módulo `gateway-go` (`go.mod`).
- [ ] Servidor HTTP/REST y gRPC en Go con enrutamiento de Auth y Matchmaking.
- [ ] Implementación de Circuit Breaker (`sony/gobreaker`) hacia PostgreSQL y Rust.
- [ ] Endpoints de salud estándar (`/healthz`, `/readyz` y `grpc.health.v1.Health`).
- [ ] Integración de Swagger UI incrustado (`/swagger/`).
- [ ] Worker pools con Goroutines para auditoría y logging asíncrono.

---

### ⏳ Fase 4: Motor de Simulación en Rust (Pendiente)
- [ ] Inicialización de proyecto Cargo `engine-rust` (`Cargo.toml` con Tokio, Tonic, Prost).
- [ ] Bucle autoritativo de juego a 20 Ticks/segundo (50ms por tick).
- [ ] Lógica física de fluidos: drenaje de embalse, fugas aleatorias, conmutación de compuertas y purificación biológica.
- [ ] Buffer de reconciliación de estados y validación de `reconnect_ticket` *(agregado por Victor)*.
- [ ] Servidor de métricas de latencia RTT (Eco Ping-Pong).

---

### ⏳ Fase 5: Clientes Multiplataforma (Pendiente)
- [ ] **Cliente Tauri (TypeScript + Vite):**
  - Configuración del proyecto y vista gráfica en Canvas 2D Top-Down.
  - Conexión directa gRPC HTTP/2 nativa sin proxy *(agregado por Victor)*.
  - HUD con widget de latencia RTT (verde/amarillo/rojo) y telemetría de embalse/pureza.
- [ ] **Cliente Python (Pygame + gRPC):**
  - Interfaz gráfica/consola interactiva con teclado.
  - Modo `--bot` inteligente autónomo para pruebas de carga y evaluación de la cátedra.

---

## 📁 Estructura de Archivos Producidos Hasta el Momento

```text
ecostream-3r/
├── .gitignore
├── README.md                                # Documentación principal y hoja de ruta
├── REQUERIMIENTOS.md.docx                   # Requerimientos académicos de la cátedra
├── scripts/
│   └── build_protos.py                      # Compilador y sincronizador de contratos
├── proto/                                   # Contratos Protocol Buffers v3
│   ├── buf.yaml                             # Configuración de linting y versionado Buf
│   ├── buf.gen.yaml                         # Generador de stubs multi-lenguaje
│   └── ecostream/
│       └── v1/
│           ├── common.proto                 # Tipos compartidos, roles y telemetría RTT
│           ├── auth.proto                   # Servicio de autenticación JWT
│           ├── matchmaking.proto            # Servicio de emparejamiento y lobbies
│           └── gameplay.proto               # Streaming 20Hz, 3R, reconexión y chat
├── client-python/
│   └── proto/                               # Stubs Python generados automáticamente
│       └── ecostream/v1/
│           ├── auth_pb2.py / auth_pb2_grpc.py
│           ├── common_pb2.py / common_pb2_grpc.py
│           ├── gameplay_pb2.py / gameplay_pb2_grpc.py
│           └── matchmaking_pb2.py / matchmaking_pb2_grpc.py
├── engine-rust/
│   └── proto/                               # Protos sincronizados para Tonic/Prost
│       └── ecostream/v1/*.proto
└── docs/
    ├── AVANCES_PROYECTO.md                  # Este documento (Bitácora de progreso)
    ├── ARQUITECTURA_Y_PLANIFICACION.md      # Diseño Zero-SPOF, Goroutines y Patrones Cloud
    ├── ARQUITECTURA_FLUJOS_Y_UML.md         # Diagramas UML y flujos de secuencia
    ├── DISENO_DEL_JUEGO.md                  # Mecánicas de las 3R y simulación hídrica
    ├── GATEWAYS_REDUNDANTES_Y_COMUNICACION.md # Explicación técnica de VIP/Keepalived
    ├── PROMPTS_DISENO_SPRITES.md            # Guía de arte Pixel Art Top-Down
    └── swagger/
        └── openapi.json                     # Especificación OpenAPI 3.0 para Swagger UI
```
