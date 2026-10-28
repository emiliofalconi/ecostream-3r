# Guía de instalación y despliegue: LAN y Render

**Proyecto:** EcoStream-3R: AquaGuardians  
**Cátedra:** Computación en la Nube — Universidad Católica Andrés Bello (UCAB)  
**Rama de referencia:** `Side-dev`

## Inicio rápido (Windows PowerShell)

```powershell
if (-not (Test-Path deployments\.env)) { Copy-Item deployments\.env.example deployments\.env }
docker compose --env-file deployments\.env -f deployments\docker-compose.yml up --build -d
npm.cmd --prefix client-tauri ci
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm.cmd --prefix client-tauri run dev -- --host 0.0.0.0 --port 5173" -WorkingDirectory (Get-Location)
Start-Sleep -Seconds 5
Start-Process "http://localhost:5173"
```

---

Esta guía cubre los requisitos, instalación de dependencias, ejecución local con Docker Compose, clientes y despliegue en Render. Para desplegar el backend no hace falta instalar Go ni Rust en la computadora si se usa Docker: ambos se compilan dentro de sus imágenes.

## 1. Arquitectura y componentes

| Componente | Tecnología | Uso |
|---|---|---|
| Gateway y matchmaking | Go, HTTP/REST y gRPC interno | API, autenticación, salas y coordinación |
| Motor de simulación | Rust, Tokio y Tonic/gRPC | Simulación autoritativa a 20 Hz |
| Base de datos | PostgreSQL 16 | Persistencia |
| Caché | Redis 7 | Caché de salas |
| Cliente Python | Python, Pygame-CE y gRPC | Cliente visual, bot y pruebas |
| Cliente web | TypeScript y Vite | Interfaz web servida localmente |

`render.yaml` define cuatro recursos: PostgreSQL, Redis, Gateway y Engine. `deployments/docker-compose.yml` añade pgAdmin, opcional, para desarrollo local.

## 2. Requisitos previos

### 2.1 Para desplegar el backend localmente

- Git para obtener el repositorio.
- Docker Desktop actualizado en Windows/macOS, o Docker Engine y Docker Compose v2 en Linux.
- Docker debe estar iniciado y el usuario debe tener permiso para ejecutar `docker`.
- Acceso a Internet durante la primera compilación para descargar imágenes y módulos.

No es necesario instalar manualmente PostgreSQL, Redis, Go, Rust ni `protoc` para el despliegue con Docker Compose.

### 2.2 Para ejecutar los clientes

- **Cliente Python:** Python 3.10 o posterior y `pip`. Las dependencias se instalan desde `requirements.txt` usando un entorno virtual.
- **Cliente web:** Node.js compatible con Vite 5 (se recomienda Node 20 LTS o 22 LTS) y npm. El lockfile está en `client-tauri/package-lock.json`.
- **Solo si se compila el backend fuera de Docker:** Go 1.26.0 o posterior según `gateway-go/go.mod`; Rust estable y `protoc` con las dependencias de compilación de Tonic/Prost.

La interfaz del directorio `client-tauri` se construye con Vite y TypeScript. Las instrucciones de esta guía ejecutan/compilan la aplicación web; no compilan un instalador nativo de Tauri.

## 3. Obtener el código

Clona el repositorio de GitHub al que tengas acceso y entra en su directorio raíz. Reemplaza la URL y la rama por las que correspondan a tu repositorio:

```bash
git clone <URL_DEL_REPOSITORIO>
cd <DIRECTORIO_DEL_REPOSITORIO>
git checkout Side-dev
```

Confirma que estás en la raíz: deben existir `render.yaml`, `deployments/`, `gateway-go/`, `engine-rust/` y `client-python/`.

## 4. Despliegue local con Docker Compose (recomendado)

### 4.1 Preparar la configuración

Compose debe leer el archivo de variables de entorno ubicado dentro de `deployments`. Copia la plantilla:

**PowerShell (Windows):**

```powershell
Copy-Item deployments\.env.example deployments\.env
```

**Linux/macOS (Bash):**

```bash
cp deployments/.env.example deployments/.env
```

Edita `deployments/.env` si necesitas cambiar puertos o configuración. Los secretos de la plantilla son únicamente para desarrollo local: **no los reutilices en producción ni publiques un `.env` con secretos reales**. El `.env` local no debe subirse al repositorio.

El script `scripts/start_local_servers.sh` usa `deployments/.env` y, si falta, avisa y cae a `.env.example`. Para los comandos manuales siguientes se recomienda crear `.env` explícitamente.

### 4.2 Validar y arrancar

Desde la raíz del proyecto:

```bash
docker compose --env-file deployments/.env -f deployments/docker-compose.yml config --quiet
docker compose --env-file deployments/.env -f deployments/docker-compose.yml up --build -d
docker compose --env-file deployments/.env -f deployments/docker-compose.yml ps
```

`up --build` compila el Gateway y el Engine desde sus Dockerfiles; PostgreSQL inicializa `deployments/postgres/schema.sql` al crear por primera vez su volumen de datos. El Gateway también ejecuta su inicialización de esquema al arrancar.

Comprueba los endpoints:

**PowerShell:**

```powershell
Invoke-WebRequest http://localhost:8080/healthz
Invoke-WebRequest http://localhost:8080/readyz
```

**Linux/macOS:**

```bash
curl -i http://localhost:8080/healthz
curl -i http://localhost:8080/readyz
```

`/healthz` debe responder HTTP 200. `/readyz` permite comprobar la conexión del Gateway a PostgreSQL y Redis. Revisa los logs si un contenedor no inicia:

```bash
docker compose --env-file deployments/.env -f deployments/docker-compose.yml logs --tail=200
docker compose --env-file deployments/.env -f deployments/docker-compose.yml logs -f gateway engine
```

Puertos publicados por Compose:

| Puerto | Servicio |
|---|---|
| `8080/tcp` | API REST del Gateway |
| `50051/tcp` | gRPC interno del Gateway |
| `50052/tcp` | gRPC del Engine |
| `5432/tcp` | PostgreSQL |
| `6379/tcp` | Redis |
| `5050/tcp` | pgAdmin opcional |

Para apagar los servicios sin borrar datos:

```bash
docker compose --env-file deployments/.env -f deployments/docker-compose.yml down
```

El volumen de PostgreSQL se conserva. **No uses `down -v` salvo que quieras eliminar permanentemente los datos locales**; el esquema SQL de inicialización no se vuelve a aplicar automáticamente sobre un volumen ya existente.

### 4.3 Conexión de clientes en LAN

El Compose de referencia usa una red bridge y la plantilla configura `ENABLE_MDNS=false`; no presupongas que Docker anunciará mDNS a la LAN. En otra computadora, usa la IP LAN del equipo anfitrión, que debe permitir tráfico entrante en los puertos necesarios:

```bash
python client-python/main_game.py --gateway http://<IP_DEL_SERVIDOR>:8080 --host <IP_DEL_SERVIDOR>:50052
```

Para probar desde la misma máquina:

```bash
python client-python/main_game.py --env local
```

La modalidad de descubrimiento mDNS requiere que el servicio esté habilitado y que la red/firewall permita multicast UDP `5353`. El cliente Python en modo automático intenta mDNS/probe y después usa Render; el Compose estándar no habilita mDNS por defecto. En redes con aislamiento de clientes Wi-Fi, usa las direcciones IP directamente.

## 5. Instalación y ejecución de clientes

### 5.1 Cliente Python

Desde la raíz, crea un entorno virtual e instala las dependencias del proyecto. El archivo raíz incluye las dependencias comunes y herramientas Protobuf:

**PowerShell (Windows):**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python client-python\main_game.py --env local
```

Si la política de PowerShell bloquea la activación del entorno, ejecuta Python por su ruta sin activar:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe client-python\main_game.py --env local
```

**Linux/macOS (Bash):**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python client-python/main_game.py --env local
```

Para instalar solo lo que declara el cliente Python, se puede usar `client-python/requirements.txt` en lugar del archivo raíz. Comprueba el entorno con:

```bash
python -m pip check
```

Ejemplos adicionales:

```bash
python client-python/bot.py --gateway http://localhost:8080 --engine localhost:50052 --duration 60
python scripts/verify_network_e2e.py --gateway http://localhost:8080 --engine localhost:50052
```

Para Render, cambia las URL al dominio real asignado a cada servicio y añade `--tls` al verificador:

```bash
python scripts/verify_network_e2e.py --gateway https://<GATEWAY>.onrender.com --engine <ENGINE>.onrender.com:443 --tls
```

### 5.2 Cliente web (Vite/TypeScript)

En Windows, abre PowerShell en la raíz del proyecto. Si PowerShell bloquea `npm.ps1` por la política de ejecución, usa `npm.cmd`; no hace falta cambiar esa política.

**Windows (PowerShell):**

```powershell
npm.cmd --prefix client-tauri ci
npm.cmd --prefix client-tauri run build
```

Para iniciar el servidor de desarrollo, ejecuta:

```powershell
npm.cmd --prefix client-tauri run dev -- --host 0.0.0.0 --port 5173
```

Deja esa terminal abierta. Cuando Vite indique que está listo, abre `http://localhost:5173` en el navegador.

**Linux/macOS (Bash):**

```bash
npm --prefix client-tauri ci
npm --prefix client-tauri run build
```

Para iniciar el servidor de desarrollo:

```bash
npm --prefix client-tauri run dev -- --host 0.0.0.0 --port 5173
```

Deja la terminal abierta y abre `http://localhost:5173` cuando Vite indique que está listo. El comando `build` genera el sitio de producción en `client-tauri/dist/`; `npm ci` instala las versiones del `package-lock.json`. En Windows, usa `npm.cmd` en lugar de `npm` para evitar el bloqueo de `npm.ps1` por la política de ejecución de PowerShell.

## 6. Despliegue en Render

### 6.1 Antes de crear el Blueprint

1. Sube a GitHub la rama que contiene `render.yaml`, los dos Dockerfiles y los archivos fuente necesarios.
2. Confirma que `render.yaml` está en la raíz del repositorio y que `dockerfilePath`/`dockerContext` corresponden a `gateway-go/` y `engine-rust/`.
3. Verifica los planes, regiones, disponibilidad de PostgreSQL/Redis y costos en Render. Los planes gratuitos y sus límites pueden cambiar; no asumas que seguirán disponibles.
4. No subas `deployments/.env`, credenciales, claves privadas ni secretos reales.

### 6.2 Crear y aplicar el Blueprint

1. En Render Dashboard, elige **New + → Blueprint**.
2. Conecta el repositorio y selecciona la rama a desplegar.
3. Revisa los cuatro recursos detectados: `ecostream-postgres`, `ecostream-redis`, `ecostream-gateway` y `ecostream-engine`.
4. Confirma la región y el plan de cada recurso y aplica el Blueprint.
5. Espera a que los dos Web Services terminen el build y pasen su health check antes de probar la aplicación.

El Blueprint configura `DATABASE_URL` y `REDIS_URL` desde los servicios administrados, genera `JWT_SECRET` y `HMAC_SECRET`, y comparte el secreto HMAC con el Engine. No reemplaces esos valores generados por los secretos de desarrollo del `.env.example`.

Render asigna `PORT` a cada Web Service. El código lee `PORT` en el Gateway y en el Engine. El endpoint público del Engine se configura en el Gateway como `<ENGINE>.onrender.com:443`; si Render asigna dominios distintos, cambias el dominio, o personalizas el nombre del servicio, actualiza `SIMULATION_PUBLIC_ENDPOINT` para que coincida con el dominio público real del Engine.

El Gateway ejecuta su inicialización de esquema al arrancar. Si `/readyz` falla, abre los logs del Gateway y verifica que sus URLs administradas de PostgreSQL y Redis estén presentes y accesibles.

### 6.3 Verificar servicios y conectividad

En Render, abre los logs y eventos de ambos Web Services. Comprueba en el navegador o con `curl`:

```bash
curl -i https://<GATEWAY>.onrender.com/healthz
curl -i https://<GATEWAY>.onrender.com/readyz
```

Después ejecuta la prueba end-to-end desde un entorno Python que tenga instaladas las dependencias del proyecto:

```bash
python scripts/verify_network_e2e.py \
  --gateway https://<GATEWAY>.onrender.com \
  --engine <ENGINE>.onrender.com:443 \
  --tls
```

La prueba verifica el Gateway, readiness, autenticación, creación de sala y la conexión al Engine. Usa los dominios reales asignados por Render, no copies literalmente los marcadores `<GATEWAY>` y `<ENGINE>`.

## 7. Compilación nativa opcional (sin Docker)

Solo se necesita para desarrollar o ejecutar directamente los backends:

- **Go:** instala Go 1.26.0 o posterior y ejecuta desde `gateway-go/`:
  ```bash
  go mod download
  go test ./...
  go build ./cmd/server
  ```
- **Rust:** instala Rust estable y Cargo, y `protoc` junto a las bibliotecas de compilación requeridas por Tonic/Prost. Desde la raíz:
  ```bash
  cargo test --manifest-path engine-rust/Cargo.toml
  cargo build --release --manifest-path engine-rust/Cargo.toml
  ```

La opción preferida para desplegar es Docker, porque los Dockerfiles instalan `protoc` y compilan cada backend en su propio entorno Linux.

## 8. Diagnóstico de problemas comunes

| Síntoma | Causa probable | Qué comprobar |
|---|---|---|
| `docker: ... daemon` o no conecta con Docker | Docker Desktop/Engine está detenido | Inicia Docker y repite `docker info`. |
| `env file ... deployments/.env not found` | No se copió la plantilla | Crea `deployments/.env` desde `.env.example`, o pasa la plantilla con `--env-file deployments/.env.example`. |
| `npm ci` dice que no encuentra lockfile | Se ejecutó desde el directorio equivocado | Ejecuta `npm --prefix client-tauri ci` desde la raíz; verifica que exista `client-tauri/package-lock.json`. |
| `npm ci` informa vulnerabilidades | Avisos de auditoría en dependencias npm | Revisa `npm --prefix client-tauri audit`; no uses `npm audit fix --force` sin revisar cambios incompatibles. |
| `pip` no encuentra un paquete | Se usó otro Python/entorno virtual | Activa `.venv`, instala el `requirements.txt` correspondiente y ejecuta `python -m pip check`. |
| Scripts `.sh` fallan en Windows | Bash/WSL no está instalado/configurado o usan una ruta Unix de `.venv` | Sigue los comandos PowerShell de esta guía, o ejecuta Bash en una distribución Linux funcional. |
| `/healthz` no responde localmente | Algún contenedor no inició o el puerto está ocupado | Revisa `docker compose ... ps` y los logs; valida firewall y puertos `8080`, `50051`, `50052`. |
| `/readyz` no está listo | PostgreSQL o Redis no está accesible | Revisa health status de dependencias y logs del Gateway. |
| Cliente no descubre servidor en LAN | mDNS deshabilitado, multicast filtrado o AP isolation | Usa `--gateway` y `--host` con la IP del servidor, y revisa firewall/puertos. |
| Render muestra `502` o health check fallido | Build/arranque fallido, servicio aún iniciando o dependencias no disponibles | Inspecciona eventos y logs del servicio y confirma el puerto `PORT` y la ruta `/healthz`. |
| El Engine no conecta desde Render | Endpoint público incorrecto o HMAC no coincide | Confirma el dominio asignado del Engine, `SIMULATION_PUBLIC_ENDPOINT` y que ambos servicios reciban el mismo `HMAC_SECRET`. |
| Error al regenerar Protobuf | Falta `protoc` o plugins de Go | Para desarrollo local instala las herramientas Protobuf correspondientes; para el despliegue Docker los Dockerfiles instalan `protoc` para Rust. |

`scripts/test_all_clients.sh` no es una verificación general de instalación en este estado del repositorio: referencia `scripts/test_contracts.py`, que no está presente, y asume un entorno Python con layout Unix (`.venv/bin/python3`). Para comprobar despliegues, usa las verificaciones de Compose y `scripts/verify_network_e2e.py` descritas arriba.
