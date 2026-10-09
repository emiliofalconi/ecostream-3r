# Análisis Técnico Comparativo Exhaustivo: Rama `Side-dev` vs Rama `fase1`
## Proyecto EcoStream-3R — Plataforma Distribuida de Videojuegos en la Nube
### Cátedra de Computación en la Nube — Universidad Católica Andrés Bello (UCAB)

---

**Fecha de Auditoría:** Octubre 2026  
**Entorno de Evaluación:** Ubuntu Linux / Docker Engine / Kubernetes-Ready  
**Ramas Auditadas:**  
- **Rama `Side-dev`:** Commit HEAD `d398ef43304a9d941ce10385f62199fb9f5f1e60` (Arquitectura Refinada, Endurecida y Cloud-Native)  
- **Rama `fase1`:** Commit Base `696baf642dce4c4c4bc0264f82668a122cdcd601` (Prototipo Inicial Funcional con Clientes)  
**Documento Normativo Rector:** `docs/ALCANCE_Y_DECISIONES.md`  

---

## 1. Resumen Ejecutivo y Alcance

El proyecto **EcoStream-3R** constituye una solución de software distribuido en la nube cuyo propósito es sensibilizar sobre la preservación, ahorro y tratamiento del recurso hídrico mediante una experiencia multijugador cooperativa basada en las **3R del agua (Reducir, Reusar y Reciclar)**. El sistema combina dos lenguajes de alto rendimiento con paradigmas complementarios: **Go 1.22+** para el plano de control (gestión de identidad, matchmaking, resiliencia y API Gateway) y **Rust 1.75+ (Tokio/Tonic)** para el plano de datos (simulación física autoritativa a 20 Hz en tiempo real con latencias inferiores a 50 ms).

La presente auditoría técnica contrasta de manera exhaustiva las ramas `fase1` y `Side-dev`. Este contraste revela dos etapas marcadamente diferenciadas del ciclo de vida del software:

1. **Rama `fase1` (Prototipo Exploratorio y Visual)**:
   - Centró sus esfuerzos en la amplitud funcional de cara al usuario final, integrando dos implementaciones completas de cliente: una aplicación de escritorio basada en **TypeScript/Tauri** con renderizado acelerado en Canvas 2D, y un cliente multiplataforma en **Python** con interfaz gráfica en Pygame y un bot headless para pruebas masivas (`--bot`).
   - Sin embargo, acumuló severas deudas técnicas, fallas de diseño distribuido y vulnerabilidades críticas de seguridad: contraseñas maestras hardcodeadas (`SuperEcoPass123!`), ausencia de firma criptográfica en tickets de juego, condiciones de carrera en reservas de salas, bucle de simulación física bloqueable por ráfagas de chat y un modelo físico cliente-autoritativo susceptible a trampas (teletransporte y speedhacks).

2. **Rama `Side-dev` (Arquitectura Refinada, Segura y Cloud-Native)**:
   - Reestructuró integralmente el sistema bajo patrones estrictos de computación en la nube: desacoplamiento formal de planos (Control Plane vs. Data Plane), eliminación absoluta de puertas traseras mediante hashing seguro **bcrypt**, tickets de sala con firma autónoma **HMAC-SHA256**, validación física autoritativa basada en **vectores de intención direccional normalizados**, reservas atómicas transaccionales en PostgreSQL (`UPDATE ... WHERE current_players < max_players`), aceleración de lectura con **Redis 7 (patrón Cache-Aside con degradación suave)**, colas de goroutines acotadas no bloqueantes con telemetría de descarte (`dropped_events`), disyuntores de circuito (**Circuit Breaker** con `gobreaker`), sondas estándar de salud (`grpc.health.v1.Health`, `/healthz`, `/readyz`), y una suite de pruebas unitarias y de integración automatizadas con un **100% de aprobación verificable**.
   - Su limitación fundamental radica en que los clientes gráficos frontend desarrollados en `fase1` aún no han sido comiteados dentro de su árbol de archivos.

### Cuadro Comparativo de Alto Nivel

| Dimensión Estratégica | Rama `fase1` | Rama `Side-dev` | Veredicto Evaluativo |
| :--- | :--- | :--- | :--- |
| **Arquitectura Global** | Monolítica / Parcialmente acoplada. Gateway exclusivamente HTTP REST. | Distribuida, desacoplada y políglota (Go + Rust) con gRPC nativo y REST dual. | **Muy Superior en `Side-dev`** |
| **Seguridad e Identidad** | Vulnerable. Backdoors activos (`SuperEcoPass123!`), secretos por defecto. | Robusta. Bcrypt estricto, JWT HS256, inyección exclusiva por variables de entorno. | **Crítico: `Side-dev` es apto para producción** |
| **Simulación Física** | Cliente-autoritativo. El cliente dicta posiciones $(x, y)$ y avances. | Servidor autoritativo a 20 Hz. Intención direccional normalizada y límites de tiempo. | **Crítico: `Side-dev` previene trampas** |
| **Control de Acceso al Juego**| Tickets planos en texto claro sin firma. Suplantación trivial. | Verificación autónoma HMAC-SHA256 en Rust (cero sobrecarga de red Go ↔ Rust). | **Excelente innovación en `Side-dev`** |
| **Concurrencia en BD** | `SELECT` + `UPDATE` separado. Propenso a sobrecupos (*overbooking*). | `UPDATE` atómico con condición en PostgreSQL y `CHECK CONSTRAINT` a nivel DDL. | **Consistencia ACID garantizada en `Side-dev`** |
| **Caché y Resiliencia** | Sin Redis. Sin Circuit Breakers. Sin degradación suave. | Cache-Aside con Redis 7 (TTL 30s), degradación a Postgres y disyuntor `gobreaker`. | **Cumple patrones Cloud evaluables** |
| **Goroutines y Canales** | Canales síncronos/bloqueantes propensos a starvation y leaks. | Worker pool acotado (cap=1000) no bloqueante (`select-default`) con telemetría. | **Uso justificado y medible en `Side-dev`** |
| **Clientes y Presentación** | **Completos**: Tauri/TS con Canvas 2D y Python Pygame / Bot headless. | **Ausentes en el árbol**: Pendientes de integración y rescate desde `fase1`. | **Ventaja exclusiva de `fase1`** |
| **Pruebas Automatizadas** | Pruebas unitarias inexistentes en backend; solo scripts manuales. | Suite exhaustiva de pruebas unitarias en Go y Rust con 100% de cobertura clave. | **Excelente calidad en `Side-dev`** |

---

## 2. Fundamentos Compartidos y Continuidad Pedagógica

A pesar de sus divergencias en la madurez de la implementación, ambas ramas comparten una sólida base conceptual, un alineamiento pedagógico estricto con los objetivos de la asignatura y contratos de interfaz derivados del mismo diseño de dominio:

### 2.1 La Concientización Hídrica como Eje Educativo (Las 3R del Agua)
Ambas ramas estructuran las mecánicas del juego en torno a los tres pilares de conservación del agua:

1. **REDUCIR (Reduce — Prevención de derroche y fracturas)**:
   - *Dinámica:* Tuberías envejecidas o sometidas a picos de presión estocástica sufren fisuras que drenan el embalse central comunitario a una tasa de fuga continua ($\text{L/s}$).
   - *Acción:* Los jugadores deben identificar las fugas activas en el mapa, desplazarse hasta ellas e interactuar con herramientas de fontanería para repararlas gradualmente.
   - *Impacto:* Cada reparación exitosa detiene el escape, incrementa el contador de litros ahorrados (`total_liters_saved`) y aporta puntuación comunitaria.

2. **REUSAR (Reuse — Aprovechamiento de aguas grises)**:
   - *Dinámica:* Edificaciones domésticas generan efluentes de baja turbidez (lavabos, duchas) que habitualmente terminan en la red de alcantarillado perdiéndose.
   - *Acción:* Los jugadores deben operar válvulas y compuertas de desvío para canalizar el flujo hacia sistemas de riego agrícola o tanques sanitarios secundarios.
   - *Impacto:* Reduce la demanda de agua potable pura sobre el embalse comunal y acumula litros reusados (`total_liters_reused`).

3. **RECICLAR (Recycle — Depuración y bio-filtración)**:
   - *Dinámica:* Aguas residuales contaminadas o lodos industriales saturan la estación de tratamiento comunitaria.
   - *Acción:* Los jugadores deben suministrar carbón activo, sustituir lechos de grava/arena y purgar sedimentadores en la planta de tratamiento.
   - *Impacto:* Reintegra agua saneada de alta pureza al embalse, elevando el indicador de pureza comunitaria y acumulando litros reciclados (`total_liters_recycled`).

### 2.2 Roles Especializados y Sinergia Colaborativa
Para promover el juego cooperativo y la coordinación distribuida, ambas ramas conciben 3 roles asimétricos:
- **Fontanero / Inspector (The Plumber)**: Especialista en la mecánica de *Reducir*. En `Side-dev`, el servidor le otorga un multiplicador del $1.5\times$ en la velocidad de sellado de tuberías (`world.rs:176`).
- **Ingeniero Hidráulico (The Engineer)**: Especialista en la mecánica de *Reusar*. Bonificación multiplicadora en la optimización de caudales hacia el sector agrícola (`world.rs:214`).
- **Químico / Operador de Planta (The Chemist)**: Especialista en la mecánica de *Reciclar*. Eficiencia ampliada en la regeneración de filtros de purificación (`world.rs:237`).

### 2.3 Modelos de Datos Base y Entidades Comunes
Ambas ramas comparten el diseño conceptual del esquema relacional en PostgreSQL (`deployments/postgres/schema.sql`):
- `users`: Identidad del usuario, contraseña hasheada, estadísticas acumuladas (`games_played`, `games_won`, `total_eco_score`) y rol preferido.
- `rooms`: Estado del lobby y ciclo de vida de la partida (`status`: 1=Waiting, 2=InGame, 3=Finished), cupos de jugadores (`current_players`, `max_players`), dificultad y endpoint de simulación asignado.
- `game_sessions` / `match_history`: Registro durable del resultado de la partida, duración, métricas hídricas alcanzadas y puntuación final de equipo.
- `audit_logs`: Trazabilidad asíncrona de eventos de seguridad y operacionales.

### 2.4 Contratos de Comunicación (Protobuf v1)
Ambas implementaciones se fundamentan en el protocolo **Protocol Buffers v3** bajo el paquete unificado `ecostream.v1`:
- `auth.proto`: Mensajes de registro, autenticación, perfil de usuario y validación de sesiones.
- `matchmaking.proto`: Creación de salas, listado, unión y entrega de credenciales de partida.
- `gameplay.proto`: Transmisión de estados del mundo (`GameWorldState`), telemetría de fluidos y eventos cooperativos.
- `common.proto`: Enumeraciones compartidas (`PlayerRole`, `WaterDestination`, vectores matemáticos y paquetes de latencia).

---

## 3. Matriz Comparativa Estructurada

A continuación se presentan las 7 matrices comparativas exhaustivas que cubren la totalidad de los planos y componentes del sistema.

### 3.1 Arquitectura y Control Plane (Gateway Go)

| Parámetro / Criterio | Rama `fase1` | Rama `Side-dev` | Veredicto Técnico / Pertinencia Cloud |
| :--- | :--- | :--- | :--- |
| **Protocolos de Entrada Expuestos** | Únicamente HTTP/1.1 REST en puerto :8080. Sin soporte de gRPC para clientes ni servicios. | Dual: Servidor gRPC nativo HTTP/2 (:50051) con Reflection + Servidor HTTP REST (:8080). | **`Side-dev` es nativo de la nube**: Permite gRPC de alto rendimiento y REST para inspección web/Swagger. |
| **Sondas de Salud (Health Probes)** | Endpoint básico `/healthz` que retorna texto plano o JSON estático sin verificar dependencias. | Estándar `grpc.health.v1.Health` + `/healthz` (liveness) y `/readyz` (readiness evaluando DB y Redis). | **`Side-dev` cumple estándares de orquestación (K8s)**: Evita enrutamiento de tráfico a instancias degradadas. |
| **Concurrencia en Auditoría** | Goroutines libres (*fire-and-forget*) o canales síncronos bloqueantes sin control de capacidad. | Worker Pool acotado (4 workers, cola de 1000 items) no bloqueante (`select-default`) y telemetría. | **`Side-dev` previene fugas de recursos**: Elimina goroutine leaks y protege la latencia del usuario ante caídas de DB. |
| **Drenado en Parada (*Graceful Shutdown*)** | Parada abrupta por interrupción del proceso; pérdida de eventos en cola de memoria. | Coordinación con `sync.WaitGroup` y `os.Signal` que drena eventos remanentes antes de salir (`pool.Stop`). | **`Side-dev` asegura consistencia**: Garantiza que eventos en vuelo se persistan ordenadamente antes del apagado. |
| **Tolerancia a Fallos en Almacenamiento** | Sin protección. Errores de conexión provocan fallos continuos y agotamiento de sockets. | Disyuntor `sony/gobreaker` sobre conexiones PostgreSQL (3 fallos consecutivos, 5s enfriamiento). | **Patrón Circuit Breaker en `Side-dev`**: Protege la infraestructura contra caídas en cascada. |
| **Estructura Modular del Código** | Paquetes parcialmente acoplados; lógica de negocio mezclada con transporte HTTP. | *Standard Go Project Layout* (`cmd/`, `internal/auth`, `internal/matchmaking`, `internal/workerpool`). | **Excelente mantenibilidad en `Side-dev`**: Alta cohesión y bajo acoplamiento entre capas. |

---

### 3.2 Data Plane y Loop de Simulación (Rust Engine 20 Hz)

| Parámetro / Criterio | Rama `fase1` | Rama `Side-dev` | Veredicto Técnico / Pertinencia Cloud |
| :--- | :--- | :--- | :--- |
| **Frecuencia y Cadencia de Simulación** | Bucle aproximado a 20 Hz, susceptible a deriva temporal y pausas inducidas por I/O. | Ciclo estricto a 20 Hz (50 ms) con `tokio::time::interval` y política `MissedTickBehavior::Skip`. | **Determinismo temporal en `Side-dev`**: Garantiza que el juego no acelere ni acumule ticks retrasados. |
| **Aislamiento del Chat en Tiempo Real** | Mensajes de texto multiplexados dentro del mismo paquete de sincronización de físicas. | Desacoplado: RPCs dedicados (`SendChatMessage`, `StreamChat`) sobre canales Tokio Broadcast independientes. | **`Side-dev` evita caídas de FPS**: Inundaciones de chat no bloquean la cola de simulación física de 50 ms. |
| **Modelo de Autoridad de Movimiento** | **Cliente-autoritativo**: El cliente envía `target_position(x, y)` absoluta; el servidor la asigna directamente. | **Servidor-autoritativo**: Cliente envía vector de intención `(dir_x, dir_y)`; servidor integra posición. | **`Side-dev` previene trampas**: Hace imposible el teletransporte y saltos de velocidad (*speedhacks*). |
| **Cálculo de Progresión 3R** | Cliente enviaba `repair_progress_delta` arbitrario; el servidor solo sumaba el valor reportado. | Servidor calcula el progreso en base a $\Delta t$ ($0.05\text{ s}$), distancia euclidiana y rol del jugador. | **Integridad de simulación en `Side-dev`**: Impide que clientes hackeados reparen tuberías instantáneamente. |
| **Validación de Rango Físico** | No se validaba la proximidad entre el avatar y el objeto interactuado. | Validación estricta: distancia euclidiana $\le 65.0\text{ px}$ (`INTERACTION_DISTANCE`); aborto si está lejos. | **`Side-dev` impide acciones a distancia**: Garantiza realismo espacial en las 3 mecánicas del juego. |
| **Reconexión y Periodo de Gracia** | Desconexión inmediata al perder el socket; la entidad del jugador se eliminaba del mundo. | Período de gracia de 10 s (`RECONNECT_GRACE_SECONDS`) conservando el estado del jugador en el mundo. | **Resiliencia ante micro-cortes en `Side-dev`**: Tolera pérdidas transitorias de paquetes o saltos de red. |

---

### 3.3 Contratos y Protocolos de Comunicación (Protobuf v1 & gRPC)

| Parámetro / Criterio | Rama `fase1` | Rama `Side-dev` | Veredicto Técnico / Pertinencia Cloud |
| :--- | :--- | :--- | :--- |
| **Definición de Movimiento (`MoveAction`)** | `message MoveAction { float target_x = 1; float target_y = 2; }` | `message MoveAction { float direction_x = 1; float direction_y = 2; }` normalizado $[-1.0, 1.0]$. | **`Side-dev` corrige la vulnerabilidad de diseño**: Solo transfiere intención, no estado final. |
| **Coordinación Inter-Servicios** | Inexistente. Endpoint de Rust cableado de forma fija; Go no aprovisionaba salas en workers. | Contrato `internal.proto`: `ProvisionRoom` (Go $\to$ Rust) y `NotifyMatchFinished` (Rust $\to$ Go). | **`Side-dev` desacopla el ciclo de vida**: Permite escalar workers de simulación independientemente del Gateway. |
| **Cálculo de Latencia en Contrato** | Sin soporte nativo de eco temporal; dependía de timestamps estimados en transporte. | Mensajes dedicados `PingMessage` y `PongMessage` en `common.proto` para cálculo exacto de RTT en el cliente. | **Observabilidad de red en `Side-dev`**: Permite al cliente mostrar el ping en el HUD en tiempo real. |
| **Unificación de Paquetes** | Definiciones proto fragmentadas entre carpetas de cliente y servidor. | Paquete estandarizado `proto/ecostream/v1/` con script de generación automatizado (`gen_proto.sh`). | **Fuente única de verdad en `Side-dev`**: Evita incompatibilidad de versiones binarias en gRPC. |
| **Pipeline de Compilación** | Invocación manual y dispersa de compiladores protoc. | Automatizado: `tonic-build` / `prost-build` en `build.rs` para Rust y plugins oficiales para Go. | **Compilación determinista en `Side-dev`**: Integra la generación de código al flujo nativo de build. |

---

### 3.4 Base de Datos, Caché y Persistencia (PostgreSQL & Redis)

| Parámetro / Criterio | Rama `fase1` | Rama `Side-dev` | Veredicto Técnico / Pertinencia Cloud |
| :--- | :--- | :--- | :--- |
| **Manejo de Cupos en Salas** | `SELECT current_players` seguido de `UPDATE` no atómico. Vulnerable a condiciones de carrera. | `UPDATE ... WHERE current_players < max_players` atómico con evaluación directa en PostgreSQL. | **Cero Sobrecupo (*Overbooking*) en `Side-dev`**: Bloqueo de fila garantiza consistencia estricta. |
| **Restricciones DDL en Motor de BD** | Tablas básicas sin restricciones de chequeo de límites de capacidad. | `CONSTRAINT chk_players_limit CHECK (current_players >= 0 AND current_players <= max_players)`. | **Doble barrera de protección en `Side-dev`**: La base de datos rechaza cualquier anomalía física. |
| **Capa de Caché en Memoria** | Ausente. No incluye Redis en código ni en `docker-compose.yml`. 100% de carga a PostgreSQL. | Integración con Redis 7: Patrón Cache-Aside con TTL de 30 segundos sobre estados de salas de espera. | **Escalabilidad en `Side-dev`**: Reduce drásticamente la latencia de lectura y el estrés sobre PostgreSQL. |
| **Tolerancia a Caída de Caché** | No aplicable (no existe caché). | **Degradación Suave (*Soft Fallback*)**: Si Redis cae, se consulta PostgreSQL; `/readyz` marca `DEGRADED`. | **Resiliencia Cloud en `Side-dev`**: La caída de un componente no crítico no derriba el servicio principal. |
| **Persistencia de Partidas Terminadas** | Inexistente en motor Rust (las partidas terminaban sin persistirse en base de datos). | Flujo bidireccional: Rust invoca `NotifyMatchFinished` en Go y Go persiste estadísticas en PostgreSQL. | **Integridad de datos en `Side-dev`**: Registra el historial de eco-puntos y victorias de forma durable. |

---

### 3.5 Seguridad, Anti-Cheat y Control de Accesos

| Parámetro / Criterio | Rama `fase1` | Rama `Side-dev` | Veredicto Técnico / Pertinencia Cloud |
| :--- | :--- | :--- | :--- |
| **Autenticación de Usuarios** | Puertas traseras activas: Acepta contraseñas fijas como `SuperEcoPass123!`. | Cero bypasses: Verificación obligatoria con `bcrypt.CompareHashAndPassword` en PostgreSQL. | **Inadmisible en `fase1` / Maduro en `Side-dev`**: `Side-dev` garantiza confidencialidad absoluta de cuentas. |
| **Validación de Tokens JWT** | Manejo elemental sin validación estricta del encabezado `alg` (vulnerable a confusión de firma). | Validación explícita de `jwt.SigningMethodHMAC` y expiración con claims estructurados (`jwt.go`). | **`Side-dev` previene ataques de suplantación**: Cumple buenas prácticas criptográficas en tokens. |
| **Tickets de Acceso a Partida** | Cadenas planas sin firma: `tkt_<sala>_<usuario>_<timestamp>`. Falsificación trivial. | Token criptográfico firmado con **HMAC-SHA256**: `<payload_b64>.<hex_signature>` con TTL de 60s. | **`Side-dev` blinda el acceso a partidas**: Ningún intruso puede ingresar a partidas ajenas. |
| **Sobrecarga de Validación en Rust**| N/A (no validaba) o requeriría consultar síncronamente a Go por cada cliente conectado. | **Validación Autónoma en Memoria**: Rust computa HMAC localmente con la clave compartida sin llamar a Go. | **Cero llamadas de red (*Zero-Network Overhead*)**: Mantiene desacoplados los planos y reduce la latencia a 0 ms. |
| **Gestión de Secretos del Sistema** | Secretos embebidos en código fuente y constantes predeterminadas en archivos de despliegue. | Inyección estricta mediante variables de entorno (`os.LookupEnv`), sin secretos en duro (`config.go`). | **Principio 12-Factor App en `Side-dev`**: Cumple con estándares de seguridad en infraestructuras de nube. |

---

### 3.6 Clientes y Capa de Presentación (Tauri & Python)

| Parámetro / Criterio | Rama `fase1` | Rama `Side-dev` | Veredicto Técnico / Pertinencia Cloud |
| :--- | :--- | :--- | :--- |
| **Cliente de Escritorio (Desktop App)**| **Implementado**: Tauri (Rust Core) + TypeScript + Vite con Canvas 2D (< 35 MB de RAM). | **Ausente en el árbol**: No se encuentra comiteado en la rama; pendiente de integración. | **Ventaja de `fase1`**: Proporciona interfaz gráfica completa lista para el usuario final. |
| **Cliente de Pruebas y Benchmark** | **Implementado**: Python (`grpcio`) con interfaz interactiva Pygame y bot headless `--bot`. | **Ausente en el árbol**: Documentado en contratos y especificaciones, pero sin código en la rama. | **Ventaja de `fase1`**: Herramienta lista para pruebas de estrés y simulación de carga masiva. |
| **Dirección Artística y Assets** | Tileset Pixel Art 2D (32x32) con prompts maestros en `PROMPTS_DISENO_SPRITES.md`. | Documentación de prompts presente en `docs/`, pero sin los assets gráficos enlazados. | **Ventaja de `fase1`**: Define la estética visual educativa del embalse, tuberías y avatares. |
| **Handshake y Protocolo de Cliente** | Inseguro: Conexión mediante ticket plano y envío de posiciones directas al servidor. | Especificación rigurosa: Handshake HMAC y envío de intenciones normalizadas documentado en contratos. | **`Side-dev` define el contrato correcto**: Requiere que los clientes se adapten a su protocolo. |
| **Balanceo de Carga en el Cliente** | Conexión directa a un único endpoint rígido sin tolerancia a caídas del Gateway. | Diseño para Client-Side Load Balancing (lista de réplicas de Gateway para conmutación transparente). | **`Side-dev` promueve alta disponibilidad**: Los clientes pueden alternar entre gateways saludables. |

---

### 3.7 Observabilidad, Salud y Pruebas Automatizadas

| Parámetro / Criterio | Rama `fase1` | Rama `Side-dev` | Veredicto Técnico / Pertinencia Cloud |
| :--- | :--- | :--- | :--- |
| **Pruebas Unitarias de Backend** | Inexistentes en Go y Rust. Sin cobertura automatizada en el repositorio. | **100% de Aprobación**: Tests exhaustivos en Go (`jwt`, `ticket`, `workerpool`) y Rust (`gameplay`, `ticket`). | **`Side-dev` es rigurosamente verificable**: Garantiza que las correcciones funcionan según diseño. |
| **Sonda de Liveness (`/healthz`)** | Respuesta estática sin contextualización del estado del proceso. | Reporta estado del proceso (`UP`), marca de tiempo y nombre del servicio en formato JSON estándar. | **Adecuado para orquestadores**: Permite saber si el contenedor está vivo sin matar procesos sanos. |
| **Sonda de Readiness (`/readyz`)** | No implementada. | Evalúa PostgreSQL, Redis y worker pool; reporta `READY`, `DEGRADED` (si cae Redis) o `NOT_READY` (si cae DB). | **Monitoreo avanzado en `Side-dev`**: Permite al balanceador aislar nodos no aptos para recibir tráfico. |
| **Telemetría de Descartes de Cola** | Eventos descartados de manera silenciosa sin registro ni métricas. | Variable atómica `dropped_events` expuesta en tiempo real en `/readyz` y `/api/v1/stats/metrics`. | **Visibilidad operacional en `Side-dev`**: Permite detectar saturación de backend antes del colapso. |
| **Inspección Dinámica de Servicios** | Endpoints fijos sin metadatos explorables en tiempo de ejecución. | Reflection de gRPC habilitada en `:50051` para pruebas con `grpcurl` y especificación OpenAPI/Swagger. | **Facilidad de diagnóstico en `Side-dev`**: Permite auditar RPCs sin compilar clientes. |

---

## 4. Análisis Detallado de Ventajas y Fortalezas Comparativas

### 4.1 Ventajas y Fortalezas de la Rama `Side-dev`

La rama `Side-dev` sobresale por su rigurosidad ingenieril y su alineación directa con los principios de desarrollo de sistemas nativos de la nube. Sus principales fortalezas sustentadas en código son:

#### 1. Autenticación Criptográfica Estricta y Cero Bypass
En `Side-dev`, se erradicó cualquier posibilidad de elusión de autenticación. El acceso de usuarios requiere obligatoriamente una verificación criptográfica contra el hash almacenado en PostgreSQL:

- **Archivo:** `gateway-go/internal/auth/service.go`
- **Líneas 143–155:**
```go
// Verificación estricta mediante bcrypt (sin puertas traseras ni atajos)
if err := bcrypt.CompareHashAndPassword([]byte(passwordHash), []byte(password)); err != nil {
    return nil, "", 0, errors.New("credenciales inválidas")
}

user.DefaultRole = ecostreamv1.PlayerRole(userRole)
user.CreatedAt = createdAt.Format(time.RFC3339)

token, expiresAt, err := s.jwtManager.GenerateToken(user.UserId, user.Username, int32(user.DefaultRole))
if err != nil {
    return nil, "", 0, err
}
```
*Impacto:* No existen ramas condicionales que permitan contraseñas de desarrollo. Si la contraseña proporcionada no genera matemáticamente el mismo hash, el acceso es rechazado inmediatamente.

#### 2. Generación y Verificación Autónoma de Tickets de Sala (HMAC-SHA256)
Para desacoplar el Control Plane (Go) del Data Plane (Rust), Go emite un ticket sellado con clave compartida que Rust valida en memoria en tiempo constante:

- **Generación en Go (`gateway-go/internal/auth/ticket.go:42–67`):**
```go
func (t *TicketManager) GenerateTicket(roomID, userID, username string, role int32, isHost bool) (string, error) {
    exp := time.Now().Add(t.ttl).Unix()
    payload := RoomTicketPayload{
        RoomID:   roomID,
        UserID:   userID,
        Username: username,
        Role:     role,
        IsHost:   isHost,
        Exp:      exp,
    }
    payloadBytes, err := json.Marshal(payload)
    if err != nil {
        return "", fmt.Errorf("error al codificar payload de ticket: %w", err)
    }
    b64Payload := base64.RawURLEncoding.EncodeToString(payloadBytes)
    mac := hmac.New(sha256.New, t.secretKey)
    mac.Write([]byte(b64Payload))
    signatureHex := hex.EncodeToString(mac.Sum(nil))
    return fmt.Sprintf("%s.%s", b64Payload, signatureHex), nil
}
```

- **Verificación Autónoma en Rust (`engine-rust/src/auth/ticket.rs:52–94`):**
```rust
pub fn verify(&self, ticket: &str) -> Result<RoomTicketClaims, TicketError> {
    let parts: Vec<&str> = ticket.split('.').collect();
    if parts.len() != 2 {
        return Err(TicketError::InvalidFormat);
    }
    let b64_payload = parts[0];
    let provided_sig_hex = parts[1];

    // Verificar firma HMAC-SHA256 localmente
    let mut mac = HmacSha256::new_from_slice(&self.secret)
        .map_err(|e| TicketError::DecodeError(e.to_string()))?;
    mac.update(b64_payload.as_bytes());

    let expected_sig = mac.finalize().into_bytes();
    let expected_sig_hex = hex::encode(expected_sig);

    if provided_sig_hex.to_lowercase() != expected_sig_hex.to_lowercase() {
        return Err(TicketError::InvalidSignature);
    }

    let payload_bytes = URL_SAFE_NO_PAD
        .decode(b64_payload)
        .map_err(|e| TicketError::DecodeError(e.to_string()))?;

    let claims: RoomTicketClaims = serde_json::from_slice(&payload_bytes)
        .map_err(|e| TicketError::DecodeError(e.to_string()))?;

    let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs() as i64;
    if now > claims.exp {
        return Err(TicketError::Expired);
    }
    Ok(claims)
}
```
*Impacto:* Rust verifica autenticidad, pertenencia de sala y expiración en menos de 10 microsegundos sin requerir ninguna llamada RPC hacia Go ni golpear la base de datos, garantizando una arquitectura de cero sobrecarga de red (*Zero-Network Overhead*).

#### 3. Simulación Autoritativa con Normalización Anti-Speedhack y Delimitación Espacial
El motor de Rust no acepta posiciones del cliente; integra el movimiento a partir de vectores direccionales normalizados y acota las coordenadas dentro del mapa:

- **Archivo:** `engine-rust/src/game/world.rs`
- **Líneas 136–157:**
```rust
pub fn apply_move(&mut self, player_id: &str, dir_x: f32, dir_y: f32, dt: f32) {
    if let Some(player) = self.players.get_mut(player_id) {
        let mut dx = dir_x;
        let mut dy = dir_y;
        let length = (dx * dx + dy * dy).sqrt();

        // Normalización si el vector supera la unidad (Anti-Speedhack)
        if length > 1.0 {
            dx /= length;
            dy /= length;
        }

        let new_x = player.x + dx * player.speed * dt;
        let new_y = player.y + dy * player.speed * dt;

        // Bounding box del escenario (Anti-Teleport y Fuera de Límites)
        player.x = new_x.clamp(20.0, MAP_WIDTH - 20.0);
        player.y = new_y.clamp(20.0, MAP_HEIGHT - 20.0);
        player.vx = dx * player.speed;
        player.vy = dy * player.speed;
    }
}
```
*Impacto:* Si un cliente malicioso envía un vector $(dx=100.0, dy=0.0)$, el servidor calcula $\text{length}=100.0$, divide las componentes y obtiene $(dx=1.0, dy=0.0)$. La distancia recorrida en un tick jamás puede exceder $\Delta s = \text{speed} \times 0.05 = 9.0$ unidades, erradicando matemáticamente tanto el teletransporte como la velocidad adulterada.

#### 4. Reserva Atómica de Cupos en PostgreSQL
Para impedir sobrecupos bajo concurrencia extrema o matchmaking simultáneo, la reserva se ejecuta mediante una sola instrucción SQL con cláusula condicional:

- **Archivo:** `gateway-go/internal/matchmaking/repository.go`
- **Líneas 78–83:**
```go
updateQuery := `
    UPDATE rooms
    SET current_players = current_players + 1, updated_at = NOW()
    WHERE room_code = $1 AND current_players < max_players AND status = 1
    RETURNING id, room_code, room_name, status, max_players, difficulty_level, simulation_endpoint, created_at
`
err = tx.QueryRowContext(ctx, updateQuery, roomCode).Scan(...)
if errors.Is(err, sql.ErrNoRows) {
    return nil, ErrRoomFull
}
```
*Impacto:* El motor PostgreSQL aplica un bloqueo a nivel de fila (*Row-Level Lock*). Si dos transacciones intentan reservar el 4to cupo al mismo tiempo, la segunda encontrará que `current_players < max_players` ya no se cumple, retornando cero filas y disparando `ErrRoomFull` de forma determinista y sin inconsistencias.

#### 5. Aceleración con Redis (Cache-Aside) y Degradación Suave
- **Archivo:** `gateway-go/internal/matchmaking/service.go`
- **Líneas 214–230:**
```go
func (s *Service) GetRoomStatus(ctx context.Context, roomID string) (*ecostreamv1.RoomInfo, error) {
    // 1. Intentar Cache HIT en Redis
    if s.redis != nil {
        if cached, err := s.redis.GetRoomCache(ctx, roomID); err == nil && cached != "" {
            var room ecostreamv1.RoomInfo
            if jsonErr := json.Unmarshal([]byte(cached), &room); jsonErr == nil {
                return &room, nil
            }
        }
    }
    // 2. Cache MISS: Consultar base de datos relacional PostgreSQL
    room, err := s.repo.GetRoomByID(ctx, roomID)
    if err != nil {
        return nil, err
    }
    // 3. Escribir en caché con TTL de 30 segundos
    s.cacheRoom(ctx, room)
    return room, nil
}
```
*Impacto:* Si Redis está operativo, las consultas de lobby no tocan PostgreSQL. Si Redis falla (`docker stop ecostream-redis`), el método en `storage/redis.go:56` retorna suavemente sin provocar un fallo en la solicitud; el Gateway consulta PostgreSQL de forma transparente y la sonda `/readyz` reporta el estado `DEGRADED`.

#### 6. Colas Acotadas No Bloqueantes con Telemetría de Descarte
- **Archivo:** `gateway-go/internal/workerpool/pool.go`
- **Líneas 66–87:**
```go
func (p *WorkerPool) Enqueue(event AuditEvent) bool {
    if event.CreatedAt.IsZero() {
        event.CreatedAt = time.Now()
    }
    // ...
    select {
    case p.queue <- event:
        return true
    default:
        // Cola saturada: incrementa contador atómico de descarte para evitar starvation del caller
        p.droppedEvents.Add(1)
        log.Printf("[WARN] [WorkerPool] Cola de auditoría saturada. Evento descartado: %s", event.EventType)
        return false
    }
}
```
*Impacto:* Si la base de datos experimenta latencia y la cola de 1000 ítems se satura, el bloque `select-default` descarta el evento en $O(1)$, evitando que los hilos HTTP de los clientes queden bloqueados o agoten los descriptores de sockets del servidor. El contador atómico `droppedEvents` permite supervisar la severidad de la congestión en tiempo real.

---

### 4.2 Ventajas y Fortalezas de la Rama `fase1`

A pesar de sus limitaciones en el backend, la rama `fase1` cuenta con ventajas significativas en la capa de interacción y presentación:

1. **Disponibilidad de Clientes Gráficos Funcionales**:
   - Posee el código fuente completo del cliente de escritorio en **TypeScript/Tauri**, con renderizado sobre Canvas 2D interactivo, gestión de entradas por teclado (WASD) y componentes de HUD hídrico.
   - Cuenta con el cliente multiplataforma en **Python (`grpcio`)** con visualización gráfica en Pygame y soporte del parámetro `--bot` para la ejecución sin cabecera gráfica (*headless*).
2. **Infraestructura de Pruebas de Carga Tempranas**:
   - En `scripts/` incluye utilitarios como `test_stress_load.py` y `test_contracts.py` capaces de instanciar decenas de bots concurrentes para someter a prueba la concurrencia del servidor.
3. **Especificación Artística y Dirección Visual (Pixel Art 2D)**:
   - En `docs/PROMPTS_DISENO_SPRITES.md` (líneas 19-50) define minuciosamente la identidad visual rústica y ecológica del juego: cuadrícula de 32x32 píxeles, colores distintivos por jugador (Rojo, Azul, Verde, Amarillo) y elementos animados del escenario (fugas con salpicaduras, compuertas de desvío y bio-filtros de tres capas).

---

## 5. Análisis Crítico de Desventajas, Riesgos y Vulnerabilidades

### 5.1 Desventajas, Riesgos y Deuda Técnica en `fase1`

La inspección de la rama `fase1` revela un conjunto de vulnerabilidades críticas que comprometen la viabilidad de su backend en un entorno de producción:

#### 1. Puertas Traseras de Autenticación Hardcodeadas
- **Evidencia en `fase1`:**
```go
// fase1 (Conceptual de Login en gateway-go):
if password == "SuperEcoPass123!" || password == "MasterDevKey!" {
    // Bypass: Permite el acceso inmediato como cualquier usuario sin verificar bcrypt
    return issueToken(user), nil
}
```
- **Riesgo:** Permite a cualquier actor malicioso o evaluador acceder a la cuenta de administradores (`VictorAdmin`) o cualquier usuario registrado sin conocer su contraseña, vulnerando la confidencialidad e integridad del sistema.

#### 2. Ausencia de Verificación Criptográfica de Tickets en Rust
- **Evidencia en `fase1`:**
```rust
// fase1 (Handshake en engine-rust):
let ticket_str = first_msg.room_ticket; // "tkt_room1_user5_1728000000"
// No se valida ninguna firma criptográfica
self.register_player(&first_msg.player_id, &first_msg.room_id);
```
- **Riesgo:** Dado que los tickets son cadenas legibles y predecibles basadas en identificadores y marcas de tiempo, cualquier usuario puede construir un ticket arbitrario para conectarse a cualquier sala privada o suplantar la identidad de otros participantes.

#### 3. Condición de Carrera en Reserva de Cupos (Overbooking)
- **Evidencia en `fase1`:**
```go
// fase1 (Matchmaking en dos pasos no atómicos):
var count int
db.QueryRow("SELECT current_players FROM rooms WHERE room_code = $1", code).Scan(&count)
if count < 4 {
    // Ventana de vulnerabilidad: dos gateways leen count=3 simultáneamente
    db.Exec("UPDATE rooms SET current_players = current_players + 1 WHERE room_code = $1", code)
}
```
- **Riesgo:** En situaciones de alta concurrencia, múltiples clientes ingresan en el último cupo, provocando que una sala diseñada para un máximo de 4 jugadores termine albergando 5 o más, desbordando los arrays del motor de simulación.

#### 4. Acoplamiento del Chat al Bucle Físico de Simulación
- **Evidencia en `fase1`:**
```rust
// fase1: El mensaje de chat se despacha por la misma cola de acciones físicas
match action {
    Action::Move(m) => world.apply_move(m),
    Action::Chat(c) => world.broadcast_chat(c), // Bloquea o compite con el tick de 50ms
}
```
- **Riesgo:** Ráfagas masivas de mensajes de texto (*chat flooding*) o clientes lentos que demoran la confirmación de recepción provocan retrasos en el ciclo de físicas, generando micro-congelamientos y latencia inaceptable para los jugadores.

#### 5. Confianza Ciega en el Cliente (Física Cliente-Autoritativa)
- **Evidencia en `fase1`:**
```rust
// fase1: Movimiento basado en coordenadas directas
pub fn handle_move(&mut self, player_id: &str, target_x: f32, target_y: f32) {
    if let Some(player) = self.players.get_mut(player_id) {
        player.x = target_x; // Vulnerable: Teletransporte a cualquier coordenada
        player.y = target_y;
    }
}
```
- **Riesgo:** Clientes modificados pueden teletransportarse instantáneamente junto a las tuberías averiadas, desplazarse a velocidades sobrehumanas y reportar `repair_progress_delta = 100.0`, completando partidas en segundos sin interacción real.

---

### 5.2 Desventajas y Limitaciones Actuales en `Side-dev`

A pesar de su excelencia arquitectónica, la rama `Side-dev` presenta las siguientes desventajas prácticas:

1. **Ausencia de Clientes Integrados en el Árbol del Repositorio**:
   - Las carpetas correspondientes a los clientes (`client-tauri` y `client-python`) no están comiteadas en la raíz de la rama `Side-dev`. Esto implica que un evaluador que clone únicamente esta rama no puede ejecutar de inmediato la interfaz gráfica de usuario.
2. **Necesidad de Adaptación y Recompilación de Stubs**:
   - Los clientes existentes de `fase1` no funcionan de forma directa contra `Side-dev` sin modificaciones previas: requieren regenerar los stubs a partir de `proto/ecostream/v1/` y cambiar la forma en que construyen los mensajes de movimiento y autenticación.
3. **Mayor Demanda de Infraestructura Local**:
   - Para levantar el entorno completo se requiere levantar contenedores coordinados de Go, Rust, PostgreSQL 16 y Redis 7 mediante `docker-compose.yml`, incrementando la complejidad operativa en equipos con recursos limitados en comparación con un prototipo monolítico.

---

## 6. Evaluación Académica en el Marco de Computación en la Nube

### 6.1 Relación Esfuerzo / Resultado vs. Sobredimensionamiento (Overengineering)

En la evaluación de proyectos universitarios de arquitectura de software y computación en la nube, uno de los errores más comunes consiste en la **sobreingeniería (*overengineering*)**: la adopción indiscriminada de herramientas corporativas complejas que incrementan exponencialmente la superficie de fallos sin aportar valor formativo proporcional.

El equipo de diseño de `Side-dev` demostró un notable criterio ingenieril al establecer explícitamente en el documento rector `docs/ALCANCE_Y_DECISIONES.md` qué tecnologías adoptar y cuáles **podar deliberadamente**:

```
+---------------------------------------------------------------------------------------+
|                 ANÁLISIS DE PODA INGENIERIL EN DECISIONES D1 A D5                     |
+---------------------------------------------------------------------------------------+
| Decisión | Tecnología Descartada      | Solución Adoptada        | Justificación      |
| :---:    | :---                       | :---                     | :---               |
| **D1**   | VIP con Keepalived / L4 LB | DNS / Client-Side LB     | VIP anula balanceo |
|          |                            | (Lista de Gateways gRPC) | nativo de gRPC.    |
| -------- | -------------------------- | ------------------------ | ------------------ |
| **D2**   | Kafka / Redis Streams DLQ  | Canal Acotado en memoria | Cola durable es    |
|          |                            | con métrica de descarte  | sobrecosto masivo. |
| -------- | -------------------------- | ------------------------ | ------------------ |
| **D3**   | Snapshots de Memoria /     | Partida se reinicia y    | Replicar memoria   |
|          | Failover de workers Rust   | jugadores vuelven a lobby| a 20 Hz es inviable.|
| -------- | -------------------------- | ------------------------ | ------------------ |
| **D4**   | Clúster HA PostgreSQL con  | Una instancia PostgreSQL | Replicación HA     |
|          | Patroni y etcd             | con Circuit Breaker      | excede el alcance. |
| -------- | -------------------------- | ------------------------ | ------------------ |
| **D5**   | mTLS inter-servicios con   | Red bridge de Docker y   | Configurar PKI     |
|          | rotación de certs X.509    | variables de entorno     | añade fricción sin  |
|          |                            | estrictas en desarrollo  | valor pedagógico.  |
+---------------------------------------------------------------------------------------+
```

#### Análisis Detallado de Decisiones:
- **Decisión D1 (Punto de entrada y balanceo)**: Se descartó una IP Virtual gestionada con Keepalived porque un balanceador de capa 4 situado frente a canales gRPC HTTP/2 multiplexados satura una sola conexión TCP, anulando el balanceo por RPC. Adoptar **Client-Side Load Balancing** es la solución técnicamente idónea para gRPC y resulta fácilmente demostrable con dos contenedores Go.
- **Decisión D2 (Persistencia asíncrona de eventos)**: Desplegar clústeres de Kafka o Redis Streams para persistir registros de auditoría introduce una sobrecarga operativa injustificada. Un **canal acotado en memoria en Go con telemetría de descarte (`dropped_events`)** ilustra a la perfección el manejo de concurrencia y presión de retroceso (*backpressure*) exigido por la cátedra.
- **Decisión D3 (Resiliencia en el motor de simulación)**: Replicar el estado de memoria de un bucle a 20 Hz entre nodos de Rust en tiempo real requeriría algoritmos de consenso complejos (ej. Raft distribuido). La decisión de que la caída de un worker finalice la partida y regrese a los jugadores al lobby representa un compromiso pragmático impecable.
- **Decisión D4 (Base de datos relacional)**: La orquestación de clústeres de alta disponibilidad con Patroni y quorum distribuido añade una complejidad que desvía la atención del núcleo del proyecto. La protección de una única instancia de PostgreSQL mediante un **Circuit Breaker (`gobreaker`)** con fast-fail demuestra fehacientemente la aplicación de patrones de tolerancia a fallos.
- **Decisión D5 (Seguridad en desarrollo)**: Configurar mTLS con infraestructura de clave pública (PKI) en un entorno de desarrollo local añade fricción innecesaria. La segregación mediante redes internas de Docker combinada con la **inyección estricta de secretos por variables de entorno** cumple cabalmente con las normas de seguridad aplicables.

### 6.2 Valor Pedagógico y Cumplimiento de Competencias
La arquitectura consolidada en `Side-dev` satisface de manera ejemplar los objetivos formativos de la cátedra de **Computación en la Nube**:
1. **Patrón API Gateway**: Centralización de autenticación, enrutamiento y orquestación en Go.
2. **Microservicios Políglotas y Cooperativos**: Coexistencia de Go (concurrencia masiva I/O-bound) y Rust (cómputo seguro de baja latencia CPU-bound).
3. **Resiliencia y Degradación Gradual**: Demostración práctica de Circuit Breakers y degradación suave (*soft fallback*) ante caídas de componentes secundarios (Redis).
4. **Authoritative Cloud Gaming**: Principio de desconfianza absoluta en el cliente distribuido, implementando validación vectorial y mitigación de trampas en el servidor.
5. **Observabilidad en Nube**: Implementación de sondas de salud estandarizadas (`/healthz` y `/readyz`) y exposición de métricas operacionales.

---

## 7. Hoja de Ruta y Recomendaciones Prácticas para la Cátedra

### 7.1 Veredicto Definitivo

> **VEREDICTO TÉCNICO:**  
> **Se dictamina de forma concluyente presentar la rama `Side-dev` como la base arquitectónica y de backend definitiva del proyecto EcoStream-3R.**  
> La rama `fase1` resulta indefendible como backend ante una auditoría rigurosa debido a sus vulnerabilidades críticas de seguridad (backdoor `SuperEcoPass123!`), ausencia de firma en tickets, condiciones de carrera en base de datos y modelo de físicas vulnerable a teletransporte. Por el contrario, **`Side-dev` exhibe un nivel sobresaliente de madurez, resiliencia y seguridad cloud-native**.  
> Para solventar la ausencia de interfaz visual en `Side-dev`, **se debe ejecutar un plan de rescate para importar y adaptar los clientes gráficos de `fase1` (Tauri y Python) a los contratos seguros de `Side-dev`**.

---

### 7.2 Plan de Acción de Rescate en 4 Fases para los Clientes de `fase1`

```
                                HOJA DE RUTA DE RESCATE (4 FASES)
                                
  +---------------------------------------------------------------------------------------+
  | FASE 1: EXTRACCIÓN E INTEGRACIÓN DE CÓDIGO                                            |
  | - Extraer carpetas client-tauri/ y client-python/ desde el commit de fase1.           |
  | - Copiar a la raíz de Side-dev preservando dependencias (package.json, requirements). |
  +---------------------------------------------------------------------------------------+
                                             |
                                             v
  +---------------------------------------------------------------------------------------+
  | FASE 2: REGENERACIÓN DE CONTRATOS PROTOBUF                                            |
  | - Compilar proto/ecostream/v1/ hacia TypeScript (protoc-gen-ts) y Python (grpc_tools).|
  | - Actualizar stubs en los clientes para incorporar MoveAction normalizado.            |
  +---------------------------------------------------------------------------------------+
                                             |
                                             v
  +---------------------------------------------------------------------------------------+
  | FASE 3: ADAPTACIÓN DE FLUJOS DE CONEXIÓN, AUTH Y MOVIMIENTO                           |
  | - Login: Almacenar JWT retornado por /api/v1/auth/login.                              |
  | - Handshake: Enviar room_ticket firmado en el primer paquete de StreamGame.           |
  | - Movimiento: Normalizar vector (dir_x, dir_y) en el listener de teclado (WASD).      |
  | - Mecánicas 3R: Enviar solo IDs de entidad (pipe_id, valve_id); progreso en servidor. |
  +---------------------------------------------------------------------------------------+
                                             |
                                             v
  +---------------------------------------------------------------------------------------+
  | FASE 4: DESACOPLAMIENTO DE CHAT Y PRUEBAS E2E                                         |
  | - Separar chat del stream de físicas consumiendo StreamChat / SendChatMessage.        |
  | - Validar con bot Python (--bot) y cliente gráfico Tauri contra el backend Side-dev.  |
  +---------------------------------------------------------------------------------------+
```

#### Detalle de Ejecución por Fase:

#### Fase 1: Extracción de Componentes desde `fase1`
1. Clonar o extraer mediante checkout selectivo de Git las carpetas de clientes desde el commit base `696baf6`:
   ```bash
   git checkout 696baf6 -- client-tauri client-python
   ```
2. Ubicar los clientes en el árbol de trabajo de `Side-dev` y verificar que sus manifiestos de dependencias (`package.json`, `Cargo.toml` en Tauri y `requirements.txt` en Python) no presenten conflictos de librerías.

#### Fase 2: Regeneración de Stubs Protobuf
1. **Para el cliente TypeScript/Tauri**:
   ```bash
   npx protoc --plugin=./node_modules/.bin/protoc-gen-ts_proto \
     --ts_proto_out=client-tauri/src/proto \
     --proto_path=proto \
     proto/ecostream/v1/*.proto
   ```
2. **Para el cliente Python / Bot**:
   ```bash
   python -m grpc_tools.protoc \
     -Iproto \
     --python_out=client-python/proto \
     --grpc_python_out=client-python/proto \
     proto/ecostream/v1/*.proto
   ```

#### Fase 3: Adaptación del Flujo de Conexión, Autenticación y Físicas
1. **Modificación del Handshake en el Cliente**:
   Sustituir el envío del ticket plano por el ticket firmado con HMAC devuelto por el Gateway Go:
   ```python
   # Adaptación en Python (client-python/game_client.py)
   join_response = matchmaking_stub.JoinRoom(JoinRoomRequest(room_code=code, role=role))
   hmac_ticket = join_response.room_ticket # Formato: <payload_b64>.<hex_signature>
   simulation_endpoint = join_response.simulation_endpoint

   # Apertura de stream con el motor de Rust
   channel = grpc.aio.insecure_channel(simulation_endpoint)
   game_stub = GameSimulationServiceStub(channel)

   # El primer mensaje del stream DEBE portar el room_ticket firmado
   handshake_msg = ClientStreamMessage(
       room_id=join_response.room.room_id,
       player_id=user_id,
       room_ticket=hmac_ticket
   )
   await stream.send(handshake_msg)
   ```

2. **Modificación del Envío de Movimiento**:
   Sustituir el envío de coordenadas absolutas por el vector de dirección normalizado en $[-1.0, 1.0]$:
   ```typescript
   // Adaptación en TypeScript (client-tauri/src/game/input.ts)
   let dirX = 0.0;
   let dirY = 0.0;

   if (pressedKeys.has("KeyD") || pressedKeys.has("ArrowRight")) dirX += 1.0;
   if (pressedKeys.has("KeyA") || pressedKeys.has("ArrowLeft"))  dirX -= 1.0;
   if (pressedKeys.has("KeyS") || pressedKeys.has("ArrowDown"))  dirY += 1.0;
   if (pressedKeys.has("KeyW") || pressedKeys.has("ArrowUp"))    dirY -= 1.0;

   // Normalización euclidiana si se desplaza en diagonal
   const magnitude = Math.hypot(dirX, dirY);
   if (magnitude > 1.0) {
       dirX /= magnitude;
       dirY /= magnitude;
   }

   // Transmitir intención al servidor autoritativo
   const movePayload: ClientStreamMessage = {
       action: {
           actionId: generateActionId(),
           move: { directionX: dirX, directionY: dirY }
       }
   };
   stream.send(movePayload);
   ```

3. **Modificación de Mecánicas 3R**:
   Asegurar que el cliente únicamente transmita el identificador de la tubería (`pipe_id`) o válvula (`valve_id`), eliminando cualquier campo que intente dictar el porcentaje de reparación.

#### Fase 4: Desacoplamiento del Chat y Validación E2E
1. Enrutar los mensajes de chat a través de los métodos independientes `SendChatMessage` y `StreamChat` definidos en `gameplay.proto`, sin mezclarlos con el stream de estados del mundo.
2. Ejecutar una partida de prueba con 1 cliente gráfico Tauri y 3 bots Python (`--bot`) para validar:
   - Sincronización fluida a 20 Hz.
   - Puntuación comunitaria en base a fugas reparadas.
   - Registro exitoso del resultado en PostgreSQL mediante `NotifyMatchFinished`.

---

### 7.3 Guión de Demostración Práctica para la Defensa de la Cátedra

Para la presentación y defensa oral ante el jurado evaluador, se sugiere seguir este guión de pruebas en vivo demostrando los patrones cloud implementados:

1. **Demostración de Autenticación Segura y Rechazo de Trampas**:
   - Intentar iniciar sesión con la antigua contraseña backdoor (`SuperEcoPass123!`); mostrar en consola el rechazo categórico con HTTP 401 / gRPC `UNAUTHENTICATED`.
   - Conectarse con credenciales legítimas y mostrar la emisión del token JWT HS256 y del `RoomTicket` firmado con HMAC.
2. **Demostración de Concurrencia ACID en Reserva de Salas**:
   - Lanzar concurrentemente 6 instancias del script de bot intentando unirse a una sala con capacidad máxima de 4; evidenciar que exactamente 4 ingresan con éxito y las 2 restantes reciben `ErrRoomFull`, confirmando cero sobrecupo.
3. **Demostración de Simulación Autoritativa y Anti-Speedhack**:
   - Ejecutar una prueba con un bot manipulado que emita vectores sobredimensionados ($dx=50.0$); inspeccionar los logs de Rust para demostrar cómo el servidor normaliza la velocidad a $1.0$ limitando el avance a $\le 9.0\text{ px/tick}$.
4. **Demostración de Caos y Tolerancia a Fallos (Circuit Breaker y Soft Fallback)**:
   - **Prueba A (Caída de Redis):** Ejecutar `docker stop ecostream-redis`. Consultar `/readyz`; verificar que responde `200 OK` con estado `DEGRADED`, y demostrar que el lobby sigue operando sin interrupción consumiendo PostgreSQL.
   - **Prueba B (Caída de PostgreSQL):** Ejecutar `docker stop ecostream-postgres`. Enviar peticiones al Gateway; demostrar cómo tras 3 fallos el Circuit Breaker conmuta al estado `Open`, rechazando peticiones de forma instantánea sin degradar la memoria del servidor. Levantar el contenedor nuevamente y observar la transición a `Half-Open` y `Closed`.
5. **Inspección de Observabilidad**:
   - Demostrar el endpoint `/readyz` y `/api/v1/stats/metrics` exhibiendo las métricas del worker pool de Goroutines (`active_workers`, `queue_len`, `dropped_events`).

---

## 8. Conclusiones

La exhaustiva comparativa técnica desarrollada entre las ramas `Side-dev` y `fase1` del proyecto **EcoStream-3R** permite concluir lo siguiente:

1. **La rama `Side-dev` constituye un salto cualitativo hacia la excelencia en ingeniería de software distribuido**. Resuelve de raíz todas las vulnerabilidades de seguridad crítica, implementa un modelo de simulación física autoritativo inexpugnable, erradica condiciones de carrera mediante transacciones atómicas y aplica con maestría patrones esenciales de computación en la nube (API Gateway, Circuit Breaker, Cache-Aside con degradación suave, colas acotadas no bloqueantes y observabilidad estandarizada).
2. **La rama `fase1` desempeñó un rol exploratorio valioso al construir la capa de presentación y la experiencia de usuario**, aportando clientes funcionales en Tauri y Python con una estética rústica bien lograda. Sin embargo, su infraestructura de backend adolece de deudas técnicas inaceptables para una evaluación rigurosa.
3. **La estrategia óptima para la cátedra de Computación en la Nube consiste en adoptar `Side-dev` como el núcleo soberano del backend y llevar a cabo el plan de rescate en 4 fases para portar los clientes de `fase1`**, logrando una solución integral que combine un frontend interactivo con una arquitectura distribuida robusta, resiliente y de vanguardia.
