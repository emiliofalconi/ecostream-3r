# Análisis de Consistencia Arquitectónica: EcoStream-3R

Este documento consolida la revisión experta (Teamwork) de la arquitectura y diseño del juego "EcoStream-3R", enfocándose en identificar fallos estructurales, cuellos de botella y escenarios de pérdida de datos.

## Resumen Ejecutivo
La arquitectura propuesta tiene una base sólida (separación de Control Plane en Go y Data Plane en Rust), pero presenta fallos críticos en sistemas distribuidos que comprometen el objetivo de "Zero-SPOF", introducen condiciones de carrera y pueden causar pérdida de datos o desincronización severa del estado del juego en los clientes.

---

## 1. Infraestructura y Redes (Agente Alpha)

### 1.1. Puntos Únicos de Fallo (SPOF) Ocultos
* **Fallo:** La arquitectura delega el estado crítico (Lobbies, Matchmaking, Snapshots de Rust) a una única instancia de Redis. Si esta instancia cae, se detiene el matchmaking y se imposibilita la recuperación ante fallos de los workers de Rust.
* **Mitigación:** Implementar una topología de Alta Disponibilidad para Redis utilizando **Redis Sentinel** (mínimo 3 nodos) o Redis Cluster, configurando los clientes (Go/Rust) para redirigir automáticamente al nuevo máster.

### 1.2. Reconexión TCP tras Fallo de Worker de Rust
* **Fallo:** El `RoomTicket` contiene un `server_endpoint` estático. Si el worker de Rust crashea y Go levanta uno nuevo en otro nodo/puerto, el cliente fallará al intentar reconectarse directamente a la IP antigua.
* **Mitigación:** Modificar el flujo de reconexión. Al caer el socket, el cliente debe consultar al Gateway Go (ej. `GetRoomEndpoint(RoomTicket)`) para obtener la nueva IP y puerto del worker recién levantado antes de intentar el TCP handshake.

### 1.3. Contradicción en Balanceo de Carga
* **Fallo:** Usar una IP Virtual (L4 VIP) junto con el balanceo de carga en cliente (Client-Side LB) nativo de gRPC es contradictorio, ya que el cliente solo vería una IP.
* **Mitigación:** Eliminar el VIP L4 y depender exclusivamente del **Balanceo basado en DNS** (ej. CoreDNS o Headless Services), usando el esquema `dns:///` en Tauri y Python para mantener múltiples conexiones simultáneas a los Gateways.

### 1.4. Tiempo de Gracia para Reconexión (5 Segundos)
* **Fallo:** 5 segundos es matemáticamente insuficiente para que Go detecte el fallo (3s de timeout de heartbeat), levante un nuevo proceso, descargue el snapshot y el cliente haga el handshake TCP/TLS.
* **Mitigación:** Incrementar el tiempo de gracia a **15 - 30 segundos**. Durante este tiempo, congelar la simulación a 20Hz (pausar el tiempo del servidor) y mostrar en el cliente una UI de "Reconectando...".

---

## 2. Backend y Gestión de Estado (Agente Beta)

### 2.1. Colas en Memoria y Pérdida de Datos (Circuit Breaker)
* **Fallo:** Si la base de datos Postgres cae, Go almacena los resultados de las partidas en una "cola en memoria" (canales de Goroutines). Si el Gateway Go se reinicia o crashea por OOM en ese momento, el historial de esas partidas se pierde irremediablemente.
* **Mitigación:** Usar **Redis Streams** como Dead Letter Queue (DLQ). Go debe hacer un append al stream (`XADD`) y un worker de fondo asíncrono debe procesarlo y hacer el `XACK` solo cuando Postgres haya vuelto y guardado la data.

### 2.2. Condiciones de Carrera en Matchmaking
* **Fallo:** Múltiples Gateways de Go pueden consultar a la vez una sala con 3 jugadores, determinar que queda 1 hueco, y asignar a múltiples jugadores a ese único hueco, sobrepasando el límite en el motor Rust.
* **Mitigación:** Usar un script Lua en Redis para consultas e incrementos atómicos del contador de jugadores, o utilizar `SELECT ... FOR UPDATE` en Postgres para bloquear la fila de la sala durante la asignación.

### 2.3. Desincronización (Split-Brain) por Rollback de Snapshots
* **Fallo:** Si los snapshots en Redis se guardan cada varios segundos, un crash de Rust implica que el nuevo worker cargará un estado "antiguo". Los clientes seguirán con el estado optimista (ej. tubería reparada), mientras el servidor retrocedió en el tiempo.
* **Mitigación:** Implementar un `sequence_id` monotónico por cada tick de 50ms. El cliente debe poder hacer un rollback de su estado local y re-aplicar inputs si recibe un snapshot con un ID más antiguo del que ya procesó.

### 2.4. Lag de Replicación Asíncrona en Postgres
* **Fallo:** La replicación asíncrona implica que en un crash duro del nodo Primario, la réplica promovida podría no tener los últimos milisegundos de transacciones confirmadas a Go.
* **Mitigación:** Generar UUIDv7 deterministas (`Match_ID`) en la creación de la sala para idempotencia. Considerar Replicación Síncrona si la pérdida cero es estricta, o retener los eventos en Redis por 5 minutos ante anomalías.

### 2.5. Autenticación Desconectada (Anti-Cheat JWT)
* **Fallo:** Si el JWT de Go usa claves asimétricas (como Ed25519), Rust necesitaría obtener las claves públicas de alguna manera, rompiendo el desacoplamiento, e imposibilitando la revocación inmediata.
* **Mitigación:** Utilizar un canal Pub/Sub ligero en Redis: Go anuncia `(room_id, valid_tickets)`. Rust se suscribe a su sala y almacena en memoria los tickets válidos (que duran solo 3-5 segundos), evitando compartir claves largas.

---

## 3. Sistemas de Juego (Agente Gamma)

### 3.1. Chat Acoplado al Game Loop (20Hz)
* **Fallo:** Procesar strings pesados dentro de la misma ventana estricta de 50ms de las físicas en Rust introduce latencia impredecible, bloat de ancho de banda y vulnerabilidad a ataques de spam (jitter de red).
* **Mitigación:** Separar el chat en un stream bidireccional gRPC distinto (`rpc ChatStream`). Tokio puede procesar este stream en una tarea asíncrona de menor prioridad sin bloquear el envío del estado de mundo (`GameWorldState`).

### 3.2. Multiplexación de Inputs (Limitación `oneof`)
* **Fallo:** El esquema Protobuf fuerza a que el jugador envíe una acción de movimiento **o** una interacción (reparar, etc) debido al uso de `oneof`. Esto impide moverse y usar mecánicas 3R simultáneamente.
* **Mitigación:** Eliminar el `oneof` en Protobuf y usar campos opcionales o repetidos (ej. `MoveAction move = 3; repeated InteractionAction interactions = 4;`).

### 3.3. Falsos Positivos de Speedhack y Reconciliación
* **Fallo:** El jitter de red (paquetes llegando todos a la vez) disparará el sistema Anti-Speedhack en Rust. Además, el servidor no acusa recibo (ACK) de qué tick del cliente procesó, haciendo imposible la Reconciliación Servidor-Cliente.
* **Mitigación:** Implementar un **Jitter Buffer** en Rust que ordene los inputs según su `client_tick_number`. Incluir un mapa `acknowledged_client_ticks` en el estado del mundo enviado por el servidor.

### 3.4. Inanición I/O por Snapshots
* **Fallo:** Escribir el estado completo en Redis a 20Hz asfixiará el I/O y la red. Escribirlo cada 5s causará demasiados rollbacks.
* **Mitigación:** Realizar escrituras asíncronas de deltas a Redis a 1Hz. Al recuperarse de un snapshot, el servidor debe enviar un flag `GameWorldStateSnapshot` que obligue a los clientes a sobreescribir forzosamente su predicción local y limpiar sus buffers.
