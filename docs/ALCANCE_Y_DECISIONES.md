# Alcance y Decisiones de Diseño: EcoStream 3R

> **Cátedra:** Computación en la Nube (UCAB - Ingeniería en Informática)
> **Propósito:** Fijar en un solo lugar **qué se construye**, **qué queda como trabajo futuro** y **qué decisiones resuelven las ambigüedades** entre los demás documentos. Si otro documento contradice a este, **este manda**.

---

## 1. Alcance del Proyecto

| Nivel | Qué incluye |
| :--- | :--- |
| **Núcleo (obligatorio)** | Registro/login con JWT y bcrypt · Crear y unirse a sala con cupo atómico · Servidor Rust autoritativo (validación de ticket, velocidad, proximidad y frecuencia de acciones) · RPC de fin de partida Rust → Go · Historial en PostgreSQL · `/healthz` y `/readyz` · Circuit Breaker · Worker Pool de goroutines · Swagger/OpenAPI · RTT visible en el cliente · Chat en tiempo real · **2 gateways** con balanceo del lado del cliente · Demo de caos (caída de Postgres y de un gateway) |
| **Deseable** | Caché de salas activas en Redis (patrón Cache-Aside) · Bonus por rol de jugador · Prueba de carga con 50–100 bots · Emulación de red con `tc netem` |
| **Trabajo futuro (fuera de alcance)** | Failover de partidas de Rust con snapshots · Réplica y promoción automática de PostgreSQL (Patroni) · mTLS entre servicios · Cola durable de eventos (Redis Streams/DLQ) · Pub/Sub entre gateways · IP virtual con Keepalived · Predicción y reconciliación en el cliente, jitter buffer y compensación de latencia |

---

## 2. Registro de Decisiones

| # | Tema | Decisión | Motivo |
| :-: | :--- | :--- | :--- |
| D1 | Punto de entrada | **DNS / lista de endpoints + balanceo del lado del cliente gRPC.** La VIP con Keepalived y el balanceador gestionado quedan como alternativas. | Una VIP delante de gRPC anula el balanceo nativo del cliente (solo ve una IP). Es más simple y es demostrable con dos contenedores. |
| D2 | Cola de fin de partida | **Canal acotado en memoria** + reintento con backoff + contador de eventos descartados + vaciado al apagar. | Redis Streams durable es sobreingeniería para este alcance. La pérdida posible se documenta y se mide. |
| D3 | Caída de un worker Rust | **La partida en curso se pierde** y los clientes vuelven al lobby. El historial ya guardado no se afecta. | Restaurar desde snapshot exige estado externo y detección de fallos no implementados. |
| D4 | PostgreSQL | **Una instancia** protegida por Circuit Breaker. La réplica y Patroni son trabajo futuro. | Replicación con promoción automática excede un proyecto escolar. |
| D5 | Seguridad entre servicios | Red Docker privada en desarrollo; **mTLS opcional en producción**. Secretos **siempre** por variable de entorno, sin valores por defecto. | Equilibrio entre seguridad y esfuerzo. |
| D6 | Firma del JWT | **HS256** con secreto compartido Go ↔ Rust. | Coincide con la implementación en `fase1`. |
| D7 | `RoomTicket` | Token **firmado con HMAC** con `room_id`, `user_id` y `exp` corto. Rust lo valida **sin consultar a Go**. | Evita tickets predecibles; no requiere Redis. |
| D8 | Contrato `PlayerAction` | Se usa el `.proto` de `fase1` como base (`oneof` con reparar, desviar y operar reciclaje). **Única diferencia:** `MoveAction` envía un **vector de intención** (`direction_x`, `direction_y`), no una posición. Moverse y actuar a la vez = dos mensajes en el mismo tick. | El cliente nunca dicta su posición (anti-teletransporte) y se evita inventar mensajes nuevos. |
| D9 | Chat | **RPC de streaming dedicado** en el mismo servicio y canal HTTP/2 de Rust. | Aísla el texto del bucle de estado sin abrir otra conexión. Es lo que define el `.proto` de `fase1`. |
| D10 | Cliente Python | **Pygame** y modo `--bot` sin interfaz. | Se descarta la TUI. |
| D11 | Cliente Tauri | **Aplicación de escritorio** con Canvas 2D. | Se descarta la variante "web". |
| D12 | Roles de jugador | **Cosméticos en el MVP**; un bonus por rol es opcional. | Hoy ninguna regla del servidor los distingue. |
| D13 | Login | La contraseña viaja por TLS (en producción) y se verifica con **bcrypt en el servidor**. | Enviar el hash lo convertiría en la contraseña real. |
| D14 | Redis | **Una sola función:** caché de salas activas con TTL. Si Redis cae, se consulta PostgreSQL. | Implementa el patrón Cache-Aside sin hacer a Redis un punto crítico. |
| D15 | Periodo de gracia | **10 segundos**, definido una sola vez como `RECONNECT_GRACE_SECONDS`. | Margen razonable ante cortes de Wi-Fi. Solo cubre micro-cortes del cliente, no caídas del servidor. |

---

## 3. Constantes Únicas

| Constante | Valor | Dónde se usa |
| :--- | :-: | :--- |
| `TICK_RATE_HZ` | 20 | Bucle de Rust (50 ms por tick) |
| `RECONNECT_GRACE_SECONDS` | 10 | Rust: tiempo que se conserva la entidad del jugador desconectado |
| `MAX_PLAYERS` | 4 | Cupo máximo por sala |
| `ROOM_TICKET_TTL` | 60 s | Vigencia del `RoomTicket` |
| `JWT_EXPIRATION_HOURS` | 24 | Vigencia del token de sesión |
| Apertura del Circuit Breaker | 3 fallos | Go hacia PostgreSQL |
| Enfriamiento del Circuit Breaker | 5 s | Paso a estado semiabierto |

---

## 4. Desviaciones Conocidas Respecto a la Rama `fase1`

La documentación describe el diseño **objetivo**. La rama `fase1` aún no lo cumple en estos puntos (revisión de octubre de 2026):

| Documentación (objetivo) | `fase1` hoy |
| :--- | :--- |
| Rust valida el `RoomTicket` firmado | No valida ningún token; el ticket es `tkt_<sala>_<usuario>_<timestamp>` sin firma |
| `MoveAction` es una intención de dirección | `MoveAction.target_position` asigna la posición directamente (teletransporte) |
| Go ↔ Rust mediante `ProvisionRoom` y `MatchFinishedEvent` | Ninguno de los dos RPC existe; el endpoint de Rust es fijo |
| Caché de salas en Redis | El código y el `docker-compose.yml` no usan Redis |
| Cupo de sala atómico | `JoinRoom` no controla el cupo |
| Login sin credenciales fijas | El login acepta dos contraseñas fijas para cualquier usuario |
| Gateway con gRPC y REST | El gateway solo expone REST/HTTP |
| Escritura del historial de partidas | El Worker Pool solo escribe `audit_logs` y descarta eventos si la cola se llena |
| Secretos por variable de entorno, sin valores por defecto | `docker-compose.yml` y `config.go` incluyen secretos por defecto |
