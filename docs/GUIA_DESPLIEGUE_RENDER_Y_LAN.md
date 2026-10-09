# Guía Oficial de Despliegue: Red Local (LAN / mDNS) y Nube (Render.com)

**Proyecto:** EcoStream-3R: AquaGuardians  
**Cátedra:** Computación en la Nube — Universidad Católica Andrés Bello (UCAB)  
**Rama Base:** `Side-dev`

---

## 1. Visión General de la Arquitectura de Despliegue

El backend de **EcoStream-3R** está desacoplado en dos capas de red:
1. **Control Plane (`gateway-go`):** Expone API REST HTTP/1.1 para Login, registro de usuarios y orquestación de salas. Administra la persistencia en PostgreSQL 16 y caché en Redis 7.
2. **Data Plane (`engine-rust`):** Motor autoritativo a 20 Hz en Rust con Tokio y Tonic gRPC sobre HTTP/2, responsable de la simulación física de fluidos, mecánicas 3R y prevención de trampas (*anti-speedhack*).

Ambos servicios están preparados para operar de forma transparente en dos modalidades:
- **Red Local Física (LAN):** Descubrimiento automático mediante **mDNS / ZeroConf**, sin requerir escribir direcciones IP.
- **Nube (Render.com):** Despliegue automatizado como infraestructura como código mediante [`render.yaml`](../render.yaml), con terminación TLS automática en el balanceador de borde.

---

## 2. Modalidad 1: Despliegue en Red Local (LAN / WiFi)

Esta modalidad está diseñada para ejecutar el servidor en una máquina anfitriona (*Server Host*) de la sala de computación o red WiFi de la universidad y permitir que múltiples laptops cliente se conecten automáticamente.

### 2.1 Puesta en Marcha con Docker Compose

Desde la raíz del repositorio:

```bash
# 1. Iniciar los 4 servicios en segundo plano
docker compose -f deployments/docker-compose.yml up -d

# 2. Verificar que los contenedores estén saludables
docker compose -f deployments/docker-compose.yml ps
```

Puertos expuestos en la máquina anfitriona:
- `:8080` $\rightarrow$ API Gateway REST (Salud, Login, Matchmaking).
- `:50051` $\rightarrow$ gRPC Coordinador Interno de Go.
- `:50052` $\rightarrow$ gRPC Motor de Simulación Rust (20 Hz).
- `:5353/udp` $\rightarrow$ Tráfico Multicast DNS para descubrimiento automático.

---

### 2.2 Descubrimiento Automático ZeroConf vía mDNS (¡Cero Configuración de IPs!)

El Gateway de Go anuncia automáticamente el servicio `_ecostream._tcp.local.` y el hostname virtual `ecostream.local` en el grupo multicast `224.0.0.251:5353`.

#### ¿Cómo se conectan los clientes en LAN?
1. **Cliente Python:** Se ejecuta con detección automática:
   ```bash
   python client-python/main_game.py --auto-discover
   ```
2. **Cliente Tauri / Web:** Al iniciar, consulta de forma transparente el hostname estándar:
   ```
   http://ecostream.local:8080
   ```
   *(Soportado nativamente por Avahi en Linux, Bonjour/mDNS en Windows 10/11 y macOS).*

#### Fallback en caso de Aislamiento de Red WiFi (AP Isolation):
Si la red WiFi del campus tiene restringido el tráfico multicast entre dispositivos, los clientes pueden ingresar directamente la IP física de la computadora anfitriona:
```bash
python client-python/main_game.py --gateway http://192.168.1.45:8080
```

---

### 2.3 Verificación de Conectividad en LAN

Ejecuta la herramienta de diagnóstico integrada:

```bash
# Modo 1: Con autodescubrimiento mDNS (¡Sin escribir IPs!)
python3 scripts/verify_network_e2e.py --auto-discover

# Modo 2: Apuntando a la IP local del anfitrión
python3 scripts/verify_network_e2e.py --host 192.168.1.45
```

---

## 3. Modalidad 2: Despliegue en la Nube (Render.com PaaS)

Render aloja el stack de forma distribuida en centros de datos con dominios HTTPS públicos y certificados SSL gestionados automáticamente.

### 3.1 Estructura del Blueprint (`render.yaml`)

El archivo [`render.yaml`](../render.yaml) define 4 componentes clave:

| Componente | Tipo de Servicio | Justificación de Arquitectura |
| :--- | :--- | :--- |
| **`ecostream-postgres`** | `postgres` (Managed DB) | Instancia PostgreSQL 16 con volumen persistente y credenciales automáticas. |
| **`ecostream-redis`** | `redis` (Managed In-Memory) | Caché volátil privada para listado de salas y fallbacks de baja latencia. |
| **`ecostream-gateway`** | `web` (Web Service) | API pública HTTPS (`:443` $\to$ `:8080`) para autenticación y matchmaking de jugadores. |
| **`ecostream-engine`** | `web` (Web Service) | **Imprescindible como Web Service.** Permite que los clientes mantengan el streaming bidireccional gRPC HTTP/2 a 20 Hz con terminación TLS. |

---

### 3.2 Pasos para Desplegar en Render

1. **Subir cambios a GitHub:**
   Asegúrate de que la rama `Side-dev` esté actualizada en tu repositorio de GitHub:
   ```bash
   git push origin Side-dev
   ```

2. **Crear Blueprint en Render Dashboard:**
   - Inicia sesión en [dashboard.render.com](https://dashboard.render.com/).
   - Haz clic en **New +** $\rightarrow$ **Blueprint**.
   - Conecta tu repositorio de GitHub y selecciona la rama `Side-dev`.
   - Render detectará automáticamente el archivo [`render.yaml`](../render.yaml) y mostrará el plan con los 4 servicios.

3. **Variables de Entorno Clave:**
   Render inyectará automáticamente las credenciales entre servicios:
   - `DATABASE_URL`: Inyectada desde `ecostream-postgres`.
   - `REDIS_URL`: Inyectada desde `ecostream-redis`.
   - `HMAC_SECRET`: Sincronizada entre el Gateway y el Motor para validar `RoomTicket`.
   - `PORT`: Asignada automáticamente por Render para enrutar el tráfico HTTP/gRPC.
   - `SIMULATION_PUBLIC_ENDPOINT`: Configurada como `ecostream-engine.onrender.com:443`.

4. **Aplicar el Blueprint:**
   Haz clic en **Apply**. Render compilará las imágenes Docker de Go y Rust e inicializará las bases de datos.

---

### 3.3 Verificación de Conectividad en Render

Una vez que los servicios figuren en verde (*Live*) en el panel de Render, ejecuta el script de validación con el flag `--tls`:

```bash
python3 scripts/verify_network_e2e.py \
  --gateway https://ecostream-gateway.onrender.com \
  --engine ecostream-engine.onrender.com:443 \
  --tls
```

El script verificará:
1. Sonda de salud y preparación (`GET /healthz` y `/readyz`).
2. Autenticación y obtención de JWT.
3. Creación de sala y extracción del ticket firmado con HMAC.
4. Conexión gRPC HTTP/2 con ALPN (`h2`) y handshake sobre TLS 1.3 con el motor de Rust.

---

## 4. Tabla de Diagnóstico y Preguntas Frecuentes

| Síntoma | Causa Posible | Solución |
| :--- | :--- | :--- |
| **`mDNS query timed out` en LAN** | El router WiFi tiene activado *Client Isolation* o el firewall bloquea el puerto UDP 5353. | Abrir el puerto 5353 en el firewall de la máquina anfitriona (`sudo ufw allow 5353/udp`) o conectar los clientes mediante `--host <IP>`. |
| **`HTTP 502 Bad Gateway` en Render al arrancar** | El servicio está en proceso de arranque o la base de datos aún no ha terminado de aplicar el esquema. | Revisar los logs en el dashboard de Render; el Gateway reintentará conectarse automáticamente. |
| **`Tonic gRPC stream disconnected`** | El ticket de sala (`RoomTicket`) ha expirado (validez por defecto: 60 segundos). | El cliente debe solicitar un nuevo ticket de reconexión al Gateway antes de reconectarse al motor. |
| **Plan Gratuito de Render entra en suspensión** | Los servicios Web gratuitos se suspenden tras 15 minutos de inactividad. | La primera petición HTTP despertará la instancia en ~30 segundos; las siguientes peticiones responderán a velocidad normal. |
