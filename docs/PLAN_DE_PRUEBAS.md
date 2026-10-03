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
   - Validar que el payload mantenga el `pipe_id` y el incremento de progreso (`repair_progress_delta`).
2. **Acción REUSAR (`DivertValveAction`):**
   - Validar conmutación de compuertas hacia `DESTINATION_IRRIGATION` (riego) o `DESTINATION_RECYCLE_PLANT`.
3. **Acción RECICLAR (`OperateRecycleAction`):**
   - Validar inserción de filtros de carbón activo y desinfección UV en planta biológica.
4. **Telemetría y Estado del Mundo (`GameWorldState`):**
   - Empaquetar métricas hídricas: nivel de embalse (%), pureza (%) y litros ahorrados.
   - Validar cálculo matemático de RTT Ping-Pong en el cliente: $\text{RTT} = \text{ClientNow} - \text{EchoTimestampMs}$.
5. **Tickets de Reconexión Rápida (`reconnect_ticket`):**
   - Verificar integridad del ticket de gracia de 5 segundos ante microcortes.

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
- Obtención de `room_code` corto (4-6 caracteres) y `RoomTicket` criptográfico.
- Apertura de stream HTTP/2 bidireccional recibiendo paquetes de estado cada 50 ms.
- Telemetría de latencia visible en consola o HUD (estado verde < 60ms en entorno local).

---

## 4. Nivel 3: Pruebas de Carga y Concurrencia Masiva (Stress Testing)

### 4.1 Objetivo
Evaluar el comportamiento y consumo de recursos de los backends (Rust y Go) ante un incremento progresivo de usuarios simultáneos en la nube.

### 4.2 Escenarios de Carga
- **Escenario Leve (Línea Base):** 5 salas, 10 bots concurrentes.
- **Escenario Medio:** 15 salas, 50 bots concurrentes.
- **Escenario Crítico (Estrés Máximo):** 25 salas, 100 bots concurrentes enviando acciones a 20 Hz (2,000 peticiones/segundo).

### 4.3 Métricas a Evaluar
1. **Estabilidad de Ticks en Rust:** Comprobar que el delta entre ticks se mantenga en $50\text{ ms} \pm 5\text{ ms}$ sin degradación severa.
2. **Consumo de Memoria:** Verificar ausencia de fugas de memoria (*memory leaks*) en el runtime de Rust y en las Goroutines de Go (`runtime.NumGoroutine()`).
3. **Uso de CPU:** Medir porcentaje de uso por núcleo en los contenedores.
4. **Latencia RTT Promedio:** Medir si la latencia promedio se mantiene por debajo de 80ms bajo carga pesada.

---

## 5. Nivel 4: Pruebas de Resiliencia y Caos (Chaos Engineering)

Para defender la arquitectura **Zero-SPOF** y el uso de **patrones nativos de la nube**, se ejecutan tres pruebas de inyección forzada de fallos:

### 5.1 Prueba A: Caída de la Base de Datos y Activación del Circuit Breaker
1. **Acción:** Detener el contenedor de base de datos durante el transcurso de una partida:
   ```bash
   docker stop postgres
   ```
2. **Comportamiento Esperado:**
   - El Gateway Go detecta la pérdida de conexión.
   - El **Circuit Breaker** (`sony/gobreaker`) conmuta a estado **`Open`** tras 3 intentos fallidos consecutivos.
   - Los eventos de cierre de partida se encolan en memoria/buffer del **Worker Pool** de Goroutines sin botar excepciones no controladas.
   - El endpoint `/readyz` responde `503 Service Unavailable`, pero el proceso Go sigue vivo (`/healthz` responde `200 OK`).
3. **Recuperación:**
   ```bash
   docker start postgres
   ```
   - El Circuit Breaker pasa a estado `Half-Open`, verifica la base de datos y se cierra (`Closed`).
   - El Worker Pool vacía automáticamente la cola de auditoría a PostgreSQL sin pérdida de historiales.

### 5.2 Prueba B: Caída Forzada del Motor de Simulación en Rust (`kill -9`)
1. **Acción:** Terminar abruptamente el proceso del motor de juego mientras una sala está activa:
   ```bash
   kill -9 <PID_RUST_ENGINE>
   ```
2. **Comportamiento Esperado:**
   - Los clientes detectan el cierre del socket gRPC y entran en modo reconexión con *Exponential Backoff*.
   - El Gateway Go detecta la ausencia de heartbeats del worker.
   - Al reiniciar el motor de Rust (o disponer de réplica secundaria), el cliente presenta su `reconnect_ticket`.
   - Si la reconexión ocurre dentro de los **5 segundos de gracia**, la partida continúa desde el snapshot de reconciliación sin reiniciar la sesión.

### 5.3 Prueba C: Conmutación de Gateways (Client-Side Load Balancing)
1. **Acción:** Detener la réplica principal de Gateway Go (`kill` a la instancia en puerto 50051).
2. **Comportamiento Esperado:**
   - El cliente gRPC (Tauri o Python) utiliza su resolver interno para conmutar inmediatamente a la réplica secundaria (puerto alterno o IP flotante VIP) en menos de 1 segundo sin interrumpir al usuario.

---

## 6. Nivel 5: Emulación de Red Degradada y Pruebas Anti-Cheat

### 6.1 Simulación de Red Inestable (Latencia y Pérdida de Paquetes)
Utilizando la utilidad de kernel de Linux `tc netem`:
```bash
# Inyectar 120 ms de retardo y 5% de pérdida aleatoria de paquetes
sudo tc qdisc add dev lo root netem delay 120ms loss 5%

# Restaurar condiciones normales de red
sudo tc qdisc del dev lo root
```
**Validación:**
- El HUD de ambos clientes debe cambiar el indicador de Ping de **Verde (< 60ms)** a **Amarillo (60-150ms)** o **Rojo (> 150ms)**.
- El algoritmo de interpolación y el margen de gracia de 5s deben evitar desconexiones accidentales por fluctuaciones normales.

### 6.2 Pruebas de Servidor Autoritativo (Anti-Cheat)
1. **Inyección de Velocidad Imposible (Speedhack):**
   - El cliente envía un vector de movimiento que supera la velocidad máxima permitida por tick ($\Delta \text{pos} > \text{max\_speed} \times \Delta t$).
   - **Resultado:** Rust descarta la posición enviada y obliga al cliente a mantenerse en su coordenada legítima.
2. **Reparación a Distancia:**
   - El cliente envía una acción `RepairPipeAction` con coordenadas lejanas a la fuga (> 1.5 tiles).
   - **Resultado:** Rust rechaza la acción por proximidad inválida.
3. **Manipulación de Token JWT:**
   - El cliente envía peticiones con una firma alterada o expirada.
   - **Resultado:** Interceptores gRPC devuelven inmediatamente código de error `UNAUTHENTICATED` (código 16 de gRPC).

---

## 7. Automatización en el Pipeline y Registro de Resultados

Para la defensa del proyecto, los resultados de la ejecución de estas pruebas se consolidarán mediante scripts dedicados:
- `scripts/test_contracts.py`: Ejecución de suite unitaria de contratos.
- `scripts/test_live_grpc.py`: Ejecución de ciclo de vida en vivo.
- `scripts/test_stress_load.py`: Lanzador masivo de bots concurrentes para captura de métricas.
