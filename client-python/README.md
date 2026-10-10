# Cliente y Bot de EcoStream-3R (Python)

Cliente y bot de simulación en tiempo real desarrollado en Python para **EcoStream-3R**, adaptado a la arquitectura desacoplada de la rama `Side-dev`.

---

## 🚀 Requisitos e Instalación

Para ejecutar los clientes de Python, instala las dependencias necesarias:

```bash
pip install -r client-python/requirements.txt
```

*(Dependencias: `grpcio`, `protobuf`, `pygame-ce`)*.

---

## 🤖 Modos de Ejecución del Bot

### 1. Bot Autónomo Headless (`bot.py`) — *Recomendado para pruebas de carga*
Ejecuta un bot de Inteligencia Artificial en consola sin interfaz gráfica. Ideal para pruebas de estrés, múltiples bots simultáneos o entornos CI/CD sin servidor X11.

```bash
# Conectar al Gateway local
python3 client-python/bot.py --username EcoBot_01 --duration 60

# Conectar al Gateway desplegado en Render
python3 client-python/bot.py \
  --gateway https://ecostream-gateway.onrender.com \
  --engine ecostream-engine.onrender.com:443 \
  --username EcoBot_Render \
  --duration 120
```

**Parámetros:**
* `--gateway`: URL del Gateway REST (ej. `http://localhost:8080`).
* `--engine`: Endpoint gRPC del motor Rust (ej. `localhost:50052` o `ecostream-engine.onrender.com:443`).
* `--username`: Nombre de usuario / Nickname (acceso sin contraseña).
* `--room`: Código de sala existente para unirse (o déjalo vacío para crear una nueva sala automáticamente).
* `--duration`: Duración de la sesión en segundos (por defecto 60).

---

### 2. Cliente de Prueba Interactivo gRPC (`test_client.py`)
Ejecuta una secuencia determinista de 6 ticks autoritativos probando el ciclo de vida completo de extremo a extremo:

```bash
python3 client-python/test_client.py --username EcoBot_Tester
```

---

### 3. Cliente Visual Gráfico en Pygame (`main_game.py`)
Permite ver al bot o jugar manualmente en una ventana interactiva de 60 FPS con partículas de agua, ondas sinusoidales en el embalse y HUD de telemetría RTT:

```bash
# Modo Bot Autónomo (La IA juega sola visualmente)
python3 client-python/main_game.py --bot --username AquaBot_01

# Modo Jugador Humano (Teclas WASD, Espacio, R, F)
python3 client-python/main_game.py --username Carlos
```

---

## 🔒 Contratos y Seguridad Implementados (`Side-dev`)

1. **Autenticación sin Contraseñas:** El bot se registra e inicia sesión enviando únicamente su `username`. El Gateway emite un token JWT.
2. **RoomTicket Criptográfico HMAC-SHA256:** El bot presenta el `room_ticket` emitido por el Gateway al conectarse al stream del motor Rust.
3. **Física Autoritativa a 20 Hz:** El cliente envía **intención direccional normalizada** (`direction_x`, `direction_y`), impidiendo hacks de velocidad o teletransporte.
4. **Mecánicas 3R Educativas:**
   * **1. Reducir:** Detección de tuberías rotas y reparación al estar a $\le 65.0$ px.
   * **2. Reusar:** Conmutación de válvulas hacia canales de riego agrícola.
   * **3. Reciclar:** Activación de bombas y reposición de filtros UV en la planta de tratamiento.
