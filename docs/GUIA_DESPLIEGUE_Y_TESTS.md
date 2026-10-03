# 🛠️ Guía de Scripts, Despliegue de Pruebas y Próximos Pasos

> **Proyecto:** EcoStream 3R - AquaGuardians 💧🌱  
> **Cátedra:** Computación en la Nube (UCAB)  
> **Estado:** Fases 0, 1, 2, 3, 4 y 5 Completadas  

---

## 📜 1. Catálogo de Scripts y Componentes

El proyecto cuenta con scripts automatizados y clientes diseñados para ser ejecutados de forma portable en Windows, Linux o macOS:

| Script / Componente | Ubicación | Funcionalidad Principal | Cómo se ejecuta |
| :--- | :--- | :--- | :--- |
| **`build_protos.py`** | [`scripts/build_protos.py`](../scripts/build_protos.py) | **Compilador de Protocol Buffers:** Instala dependencias, compila todos los `.proto` a stubs de Python tipados (`*_pb2.py`, `*.pyi`) y sincroniza los contratos para el motor de Rust. | `python scripts/build_protos.py` |
| **`test_contracts.py`** | [`scripts/test_contracts.py`](../scripts/test_contracts.py) | **Suite de Validación de Contratos:** Verifica la serialización binaria de las acciones 3R, el `GameWorldState` a 20 Hz, la telemetría RTT y la validez de OpenAPI 3.0. | `python scripts/test_contracts.py` |
| **`test_live_grpc.py`** | [`scripts/test_live_grpc.py`](../scripts/test_live_grpc.py) | **Test de Integración gRPC en Vivo:** Simula el ciclo de vida completo: Login JWT, Matchmaking y streaming continuo a 20 Hz con Ping-Pong de telemetría. | `python scripts/test_live_grpc.py` |
| **`main_game.py` (Pygame / Bot)** | [`client-python/main_game.py`](../client-python/main_game.py) | **Cliente Gráfico Pygame & Bot Autónomo:** Renderizado 2D de zonas 3R, controles interactivos de teclado (`WASD`, `Espacio`, `R`, `F`), widget de latencia RTT y modo `--bot` para pruebas de estrés. | `python client-python/main_game.py` (Humano)<br>`python client-python/main_game.py --bot` (Bot) |
| **Cliente Web / Tauri** | [`client-tauri/`](../client-tauri/) | **Cliente Web / Desktop (TS + Canvas 2D):** HUD con telemetría en vivo, canvas reactivo a 60 FPS con animación hídrica y acciones 3R. | `cd client-tauri && npm run dev` |
| **`mock_server.py`** | [`client-python/mock_server.py`](../client-python/mock_server.py) | **Servidor Simulado Standalone:** Servidor gRPC que implementa los servicios en el puerto `50051` para pruebas aisladas. | `python client-python/mock_server.py` |

---

## 🚀 2. Guía Paso a Paso de Despliegue y Ejecución Local

### Prerrequisitos
1. **Python 3.10+** con `pygame-ce` (`pip install pygame-ce grpcio grpcio-tools`).
2. **Node.js 18+** (para el cliente Web/Tauri).
3. **Docker Desktop** (abierto y en ejecución).

---

### Paso 2.1: Levantar Todo el Stack en Docker
Abre una terminal en la raíz del proyecto y ejecuta:
```powershell
docker compose -f deployments/docker-compose.yml up -d --build
```

Servicios activos:
* **PostgreSQL 16:** `localhost:5432` (`ecostream_db`).
* **Gateway en Go:** `http://localhost:8080` (HTTP REST) y `localhost:50051` (gRPC).
  * **Swagger UI interactivo:** [http://localhost:8080/swagger/](http://localhost:8080/swagger/)
  * **Health Liveness:** `http://localhost:8080/healthz`
  * **Health Readiness:** `http://localhost:8080/readyz`
* **Motor de Simulación en Rust:** `localhost:50052` (Streaming gRPC autoritativo a 20 Hz).
* **pgAdmin 4:** [http://localhost:5050](http://localhost:5050) (Email: `admin@ecostream.ucab.ve`, Pass: `admin123`).

---

### Paso 2.2: Ejecutar el Cliente Gráfico de Python (Modo Jugador Humano)
Para jugar interactivamente conectado al motor de simulación Rust a 20 Hz:
```powershell
python client-python/main_game.py
```
* **Controles:**
  * `W, A, S, D` / Flechas: Mover avatar del jugador.
  * `Espacio`: **1. Reducir** (Reparar fugas de agua más cercanas).
  * `R`: **2. Reusar** (Conmutar válvula de aguas grises hacia huertos).
  * `F`: **3. Reciclar** (Cargar filtros de carbón/UV en la planta biológica).
  * `ESC`: Salir.

---

### Paso 2.3: Ejecutar el Modo Bot Autónomo (Pruebas de Carga y Evaluación)
Para ejecutar un agente con inteligencia artificial que detecta y repara fugas automáticamente:
```powershell
python client-python/main_game.py --bot
```

---

### Paso 2.4: Ejecutar el Cliente Web / Tauri (TypeScript + Canvas 2D)
Para iniciar el servidor de desarrollo Vite con la interfaz visual reactiva:
```powershell
cd client-tauri
npm run dev
```
Abre [http://localhost:5173](http://localhost:5173) en el navegador.

---

### Paso 2.5: Recompilar Protocol Buffers (Opcional)
Si modificas algún archivo `.proto` en `proto/ecostream/v1/`:
```powershell
python scripts/build_protos.py
```

---

### Paso 2.6: Ejecutar la Suite de Pruebas Unitarias de Contratos
```powershell
python scripts/test_contracts.py
```
