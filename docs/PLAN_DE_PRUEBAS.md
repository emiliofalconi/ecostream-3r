# Plan Maestro de Pruebas y Validación: EcoStream 3R

> **Cátedra:** Computación en la Nube  
> **Institución:** Universidad Católica Andrés Bello (UCAB) - Escuela de Ingeniería en Informática  
> **Objetivo:** Documentar y sistematizar los escenarios de prueba unitarios, de integración, de resiliencia ante fallos, de estrés masivo y de conformidad cloud-native para la evaluación del sistema distribuido.

---

## 1. Matriz General de Niveles de Prueba

El plan de pruebas se estructura en 5 niveles complementarios diseñados para validar tanto la lógica de negocio como los atributos de calidad de la nube (disponibilidad, elasticidad, rendimiento y seguridad):

| Nivel | Tipo de Prueba | Herramienta / Tecnología | Objetivo Principal |
| :-: | :--- | :--- | :--- |
| **Nivel 1** | **Integridad de Contratos gRPC** | Python (`pytest` / `unittest`), Protobuf | Verificar serialización binaria de acciones 3R, telemetría RTT y esquemas OpenAPI. |
| **Nivel 2** | **Flujo Interactivo End-to-End** | Python (`grpcio`), Mock Server / Live Engine | Simular el ciclo de vida completo: Login -> Matchmaking -> Streaming 20Hz. |
| **Nivel 3** | **Carga Masiva y Concurrencia** | Python (`asyncio` + `grpc.aio`), Bots autónomos | Estresar el motor de Rust y los gateways de Go con 20 a 100 clientes concurrentes. |
| **Nivel 4** | **Ingeniería del Caos y Resiliencia** | Docker CLI, Linux `kill`, Circuit Breakers | Validar recuperación ante caída de PostgreSQL, caída de workers Rust y failover de Gateways. |
| **Nivel 5** | **Emulación de Red y Anti-Cheat** | Linux `tc` (Traffic Control), clientes alterados | Evaluar tolerancia a latencia (>150ms), pérdida de paquetes (5%) y rechazo de trampas. |

---

## 2. Nivel 1: Pruebas de Integridad de Contratos Protobuf

### 2.1 Casos de Prueba
1. **Acción REDUCIR (`RepairPipeAction`):**
   - Serializar y deserializar paquete binario de soldadura/reparación de tubería.
   - Validar que el payload mantenga el `pipe_id`. El progreso de reparación lo calcula el servidor; el cliente no envía incrementos (principio de cero confianza).
2. **Acción REUSAR (`DivertValveAction`):**
   - Validar conmutación de compuertas hacia `DESTINATION_IRRIGATION` (riego) o `DESTINATION_RECYCLE_PLANT`.
3. **Acción RECICLAR (`OperateRecycleAction`):**
   - Validar inserción de filtros de carbón activo y desinfección UV en planta biológica.
4. **Telemetría y Estado del Mundo (`GameWorldState`):**
   - Empaquetar métricas hídricas: nivel de embalse (%), pureza (%) y litros ahorrados.
   - Validar cálculo matemático de RTT Ping-Pong en el cliente: $\text{RTT} = \text{ClientNow} - \text{EchoTimestampMs}$.
5. **Tickets de Reconexión Rápida (`reconnect_ticket`):**
   - Verificar que el ticket (token aleatorio de ≥ 128 bits) sea aceptado dentro de la gracia de 10 segundos (`RECONNECT_GRACE_SECONDS`) y rechazado después.

---

## 3. Nivel 2: Pruebas de Integración End-to-End (E2E)

### 3.1 Flujo Evaluado
```
[Cliente gRPC] ----> 1. Login (JWT) ----> 2. CreateRoom (RoomTicket) ----> 3. Stream 20Hz (Acciones 3R)
                           |                            |                               |
                     Go Gateway                    Go Gateway                      Rust Engine
```

### 3.2 Criterio de Éxito
- Recepción de token JWT con expiración válida.
- Obtención de `room_code` corto (4-6 caracteres) y `RoomTicket` firmado con HMAC y expiración corta (60 s).
- Apertura de stream HTTP/2 bidireccional recibiendo paquetes de estado cada 50 ms.
- Telemetría de latencia visible en consola o HUD (estado verde < 60ms en entorno local).

---

## 4. Nivel 3: Pruebas de Carga y Concurrencia Masiva (Stress Testing)

### 4.1 Objetivo
Evaluar el comportamiento y consumo de recursos de los backends (Rust y Go) ante un incremento progresivo de usuarios simultáneos en la nube.

### 4.2 Escenarios de Carga
- **Escenario Leve (Línea Base):** 5 salas, 10 bots concurrentes.
- **Escenario Medio:** 15 salas, 50 bots concurrentes.
- **Escenario Crítico (Estrés Máximo) — *Opcional*:** 25 salas, 100 bots concurrentes enviando acciones a 20 Hz (2,000 peticiones/segundo). Depende de la capacidad de la máquina de pruebas.

### 4.3 Métricas a Evaluar
1. **Estabilidad de Ticks en Rust:** Comprobar que el delta entre ticks se mantenga en $50\text{ ms} \pm 5\text{ ms}$ sin degradación severa.
2. **Consumo de Memoria:** Verificar ausencia de fugas de memoria (*memory leaks*) en el runtime de Rust y en las Goroutines de Go (`runtime.NumGoroutine()`).
3. **Uso de CPU:** Medir porcentaje de uso por núcleo en los contenedores.
4. **Latencia RTT Promedio:** Medir si la latencia promedio se mantiene por debajo de 80ms bajo carga pesada.

---

## 5. Nivel 4: Pruebas de Resiliencia y Caos (Chaos Engineering)

Para defender la arquitectura (sin SPOF en la entrada) y el uso de **patrones nativos de la nube**, se ejecutan pruebas de inyección forzada de fallos. Los resultados esperados corresponden al alcance definido en [ALCANCE_Y_DECISIONES.md](ALCANCE_Y_DECISIONES.md).

### 5.1 Prueba A: Caída de la Base de Datos y Activación del Circuit Breaker
1. **Acción:** Detener el contenedor de base de datos durante el transcurso de una partida:
   ```bash
   docker stop postgres
   ```
2. **Comportamiento Esperado:**
   - El Gateway Go detecta la pérdida de conexión.
   - El **Circuit Breaker** (`sony/gobreaker`) conmuta a estado **`Open`** tras 3 intentos fallidos consecutivos.
   - Los eventos de cierre de partida se encolan en la **cola acotada** del **Worker Pool** de Goroutines, con reintento y backoff exponencial, sin botar excepciones no controladas.
   - El endpoint `/readyz` responde `503 Service Unavailable`, pero el proceso Go sigue vivo (`/healthz` responde `200 OK`).
   - Las partidas en curso en Rust **continúan** con normalidad.
3. **Recuperación:**
   ```bash
   docker start postgres
   ```
   - El Circuit Breaker pasa a estado `Half-Open`, verifica la base de datos y se cierra (`Closed`).
   - El Worker Pool vacía la cola a PostgreSQL. **No hay pérdida de historiales mientras la cola no se llene**; si se llena, el contador de descartes (visible en `/readyz`) refleja exactamente cuántos eventos se perdieron.

### 5.2 Prueba B1: Caída Forzada del Motor de Simulación en Rust (`kill -9`)
1. **Acción:** Terminar abruptamente el proceso del motor de juego mientras una sala está activa:
   ```bash
   kill -9 <PID_RUST_ENGINE>
   ```
2. **Comportamiento Esperado:**
   - Los clientes detectan el cierre del stream gRPC y muestran el mensaje "Partida interrumpida".
   - El Gateway Go detecta la ausencia de heartbeats del worker y marca la sala como `FINISHED`.
   - Los clientes vuelven al lobby y pueden crear una sala nueva. **La partida en curso se pierde** (la restauración desde snapshot es trabajo futuro) y el historial ya guardado no se afecta.

### 5.3 Prueba B2: Micro-corte de Red del Cliente (Reconexión con Ticket)
1. **Acción:** Interrumpir la red de un solo cliente durante 5 segundos (por ejemplo, desconectar el Wi-Fi o bloquear el puerto con `iptables`) y restablecerla.
2. **Comportamiento Esperado:**
   - El cliente muestra "Reconectando..." y reintenta con *Exponential Backoff*.
   - Si la reconexión ocurre dentro de los **10 segundos de gracia** (`RECONNECT_GRACE_SECONDS`), el cliente presenta su `reconnect_ticket` y recibe un snapshot de reconciliación; la partida continúa sin reiniciar la sesión.
   - Si el corte supera los 10 segundos, el jugador es retirado de la sala.

### 5.4 Prueba C: Conmutación de Gateways (Client-Side Load Balancing)
1. **Acción:** Con dos réplicas del Gateway Go en puertos o hosts distintos (el cliente configurado con la lista de ambos endpoints), detener la réplica que está atendiendo (`kill` o `docker stop`).
2. **Comportamiento Esperado:**
   - El cliente gRPC (Tauri o Python) utiliza su resolver interno para conmutar a la réplica secundaria en menos de 1 segundo, sin interrumpir al usuario y sin necesidad de una IP virtual.

---

## 6. Nivel 5: Emulación de Red Degradada y Pruebas Anti-Cheat

### 6.1 Simulación de Red Inestable (Latencia y Pérdida de Paquetes) — *Opcional*
Utilizando la utilidad de kernel de Linux `tc netem`:
```bash
# Inyectar 120 ms de retardo y 5% de pérdida aleatoria de paquetes
sudo tc qdisc add dev lo root netem delay 120ms loss 5%

# Restaurar condiciones normales de red
sudo tc qdisc del dev lo root
```
**Validación:**
- El HUD de ambos clientes debe cambiar el indicador de Ping de **Verde (< 60ms)** a **Amarillo (60-150ms)** o **Rojo (> 150ms)**.
- La interpolación en el cliente y el margen de gracia de 10 s deben evitar desconexiones accidentales por fluctuaciones normales.

### 6.2 Pruebas de Servidor Autoritativo (Anti-Cheat)
1. **Vector de Movimiento Excesivo (Speedhack):**
   - El cliente envía un `MoveAction` con un vector de magnitud mayor a 1 (por ejemplo, `direction_x = 50`).
   - **Resultado:** Rust normaliza el vector y limita el desplazamiento a `max_speed × Δt` por tick. El teletransporte no es posible por diseño, porque el cliente nunca envía una posición.
2. **Reparación a Distancia:**
   - El cliente envía una acción `RepairPipeAction` estando a más de 1.5 tiles de la fuga.
   - **Resultado:** Rust rechaza la acción por proximidad inválida.
3. **Manipulación de Token JWT:**
   - El cliente envía peticiones al Gateway con una firma alterada o expirada.
   - **Resultado:** Los interceptores gRPC devuelven inmediatamente `UNAUTHENTICATED` (código 16 de gRPC).
4. **`RoomTicket` Inválido o Expirado:**
   - El cliente abre el stream hacia Rust con un ticket alterado, de otra sala o vencido (> 60 s).
   - **Resultado:** Rust cierra el stream con `UNAUTHENTICATED` sin crear ninguna sala.
5. **Flood de Acciones:**
   - El cliente envía más acciones por segundo que el límite configurado.
   - **Resultado:** Rust descarta el exceso sin afectar el tick de los demás jugadores.

---

## 7. Automatización en el Pipeline y Registro de Resultados

Para la defensa del proyecto, los resultados de la ejecución de estas pruebas se consolidarán mediante scripts dedicados (ubicados en la rama `fase1`, no en la rama de documentación):
- `scripts/test_contracts.py`: Ejecución de suite unitaria de contratos.
- `scripts/test_live_grpc.py`: Ejecución de ciclo de vida en vivo.
- `scripts/test_stress_load.py`: Lanzador masivo de bots concurrentes para captura de métricas.
