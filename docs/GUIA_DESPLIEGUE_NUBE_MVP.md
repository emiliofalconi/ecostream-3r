# ☁️ Guía Rápida de Despliegue en la Nube (MVP): EcoStream 3R
**Cátedra:** Computación en la Nube (UCAB)  
**Objetivo:** Desplegar PostgreSQL 16, Gateway Go y Motor Rust en una Máquina Virtual con IP Pública.

---

## 1. Opciones de Nube Recomendadas (Nivel Gratuito / Free Tier)
1. **Oracle Cloud Infrastructure (OCI):** Compute Instance Always Free (Ubuntu 22.04 LTS o 24.04).
2. **AWS EC2:** Instancia `t2.micro` o `t3.micro` en el nivel gratuito de 12 meses.
3. **Google Cloud (GCP):** Instancia `e2-micro` Always Free.
4. **DigitalOcean / Linode:** Droplet básico de $4-6/mes.

---

## 2. Puertos que debes abrir en el Firewall / Security Group de la Nube

| Servicio | Puerto | Protocolo | Descripción |
| :--- | :---: | :---: | :--- |
| **SSH** | `22` | TCP | Acceso y administración remota |
| **Go Gateway HTTP** | `8080` | TCP | REST API, Matchmaking, Swagger y Healthchecks |
| **Go Gateway gRPC** | `50051` | TCP | Llamadas RPC de Control Plane |
| **Rust Engine gRPC** | `50052` | TCP | Streaming en tiempo real a 20Hz (Física autoritativa) |
| **PostgreSQL** | `5432` | TCP | Acceso a base de datos (restringir a la IP del equipo) |
| **pgAdmin 4 (Opcional)**| `5050` | TCP | Interfaz web de base de datos |

---

## 3. Comandos de Instalación en la Máquina Virtual (Ubuntu / Debian)

Conéctate por SSH a tu servidor:
```bash
ssh -i tu_llave.pem ubuntu@TU_IP_PUBLICA
```

### Paso A: Instalar Docker y Docker Compose
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git ufw

# Instalar Docker Engine
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

### Paso B: Clonar el Repositorio
```bash
git clone -b fase1 https://github.com/Makmadon/ecostream-3r.git
cd ecostream-3r
```

### Paso C: Configurar Variables de Entorno
```bash
cp .env.example .env
# Si deseas cambiar contraseñas de producción:
nano .env
```

### Paso D: Levantar los Contenedores
```bash
docker compose -f deployments/docker-compose.yml up -d --build
```

---

## 4. Verificación de Salud del Despliegue Cloud

Ejecuta desde tu terminal local o navegador web:
```bash
# 1. Comprobar que el Gateway Go esté vivo en la IP pública:
curl http://TU_IP_PUBLICA:8080/healthz

# 2. Comprobar que la base de datos y Rust estén listos:
curl http://TU_IP_PUBLICA:8080/readyz

# 3. Probar la documentación interactiva en el navegador:
# Abre: http://TU_IP_PUBLICA:8080/swagger/
```

---

## 5. Cómo Conectarse desde las Casas del Equipo

### Opción 1: Cliente Web / Tauri (TypeScript)
1. Abre el juego en tu navegador o cliente Tauri (`npm run dev`).
2. En la barra superior, haz clic en **🌐 Salas Go**.
3. En el campo **"Servidor Cloud / IP Pública"**, ingresa la IP de la máquina virtual (ejemplo: `http://54.210.88.12:8080`).
4. ¡Listo! Verás el indicador en verde `🟢 Conectado: http://54.210.88.12:8080 (:8080) - Listo` y podrás crear o unirte a salas remotas.

### Opción 2: Cliente Python (Pygame y Bots)
Pasa el flag `--host` con la IP pública de la nube:
```bash
# Modo humano interactivo:
python client-python/main_game.py --host TU_IP_PUBLICA:50052 --player Jugador_Remoto_1

# Modo Bot inteligente autónomo (A*):
python client-python/main_game.py --host TU_IP_PUBLICA:50052 --bot --player Bot_Remoto_1
```
