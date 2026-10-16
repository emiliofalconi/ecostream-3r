# ⚖️ Balanceo de Juego y Diseño Final (Game Design)
**Proyecto:** EcoStream 3R - AquaGuardians  
**Cátedra:** Computación en la Nube - UCAB  
**Rol:** DevOps / Game Design  
**Fecha:** Octubre 2026  
**Archivo Autoritativo:** [`engine-rust/src/simulation/world.rs`](file:///C:/Users/Malwer/Documents/antigravity/intelligent-bose/ecostream-3r/engine-rust/src/simulation/world.rs)  

---

## 1. Filosofía de Balanceo y Experiencia del Jugador (UX)

EcoStream 3R fue diseñado como un videojuego cooperativo distribuido en tiempo real que combina desafíos mecánicos (pathfinding, timing, interacción espacial) con sensibilización sobre el **ODS 6 (Agua Limpia y Saneamiento)**.

El objetivo del balanceo final es garantizar una curva de tensión justa pero exigente:
- **Partida Solitario / Con Bot:** Es viable sobrevivir si el jugador o bot prioriza las fugas críticas y no malgasta tiempo en el mapa.
- **Partida Cooperativa (2-4 Jugadores):** Fomenta la división de roles: un jugador repara tuberías a alta presión (Ingeniero Hidráulico), otro conmuta válvulas de riego (Operador Comunitario), y otro mantiene la pureza del agua en la planta de tratamiento (Especialista en Tratamiento).
- **Prevención de Victorias Triviales:** Los eventos climáticos dinámicos introducen picos de estrés hídrico que impiden que el equipo se desentienda del embalse.

---

## 2. Parámetros Numéricos Calibrados en Producción

### 2.1. Temporización y Cadencia
| Parámetro | Valor Calibrado | Justificación de Game Design |
| :--- | :---: | :--- |
| **Duración de la Partida** | `180 segundos` (3 minutos) | Duración ideal para rondas ágiles y competitivas sin fatiga de usuario. |
| **Frecuencia del Bucle (Tick Rate)** | `20 Hz` (50 ms por tick) | Estándar de la industria para juegos multijugador competitivos de bajo retardo. |
| **Total de Ticks por Partida** | `3,600 ticks` | `180s * 20 ticks/s`. |
| **Intervalo de Nuevas Fugas** | `260 ticks` (~13.0 segundos) | Ofrece margen suficiente para desplazarse por el mapa antes de que aparezca una nueva rotura. |
| **Presión del Agua en Red** | `3.5 - 4.5 bar` | A mayor presión, mayor es el caudal de pérdida de la tubería. |

---

### 2.2. Ecuación Autoritativa del Embalse y Drenaje

El volumen del embalse se calcula en cada tick (50 ms) siguiendo la ecuación de balance de masa:

$$\text{Nivel}_{t+1} = \text{clamp}\left(\left[\text{Nivel}_t - \text{DrenajeEfectivo}_t\right] + \text{AporteLluvia}_t, \ 0.0, \ 100.0\right)$$

Donde el drenaje efectivo está compuesto por:
$$\text{DrenajeBase} = 0.0035 + \left(\sum \text{CaudalFugas (L/s)} \times 0.0009\right)$$
$$\text{DrenajeEfectivo} = \text{DrenajeBase} \times \text{MultiplicadorClimático}$$

#### Comparativa de Tasas de Pérdida por Escenario:
1. **Red Óptima (Sin Fugas, Clima Normal):**
   - Drenaje por tick: `0.0035%`
   - Drenaje por segundo (20 ticks): `0.07% / s`
   - Pérdida acumulada en 3 minutos: **~12.6%** (Consumo comunal sostenible de la población).
2. **Red con 2 Fugas Activas (15 L/s en total):**
   - Drenaje por tick: `0.0035 + (15.0 * 0.0009) = 0.0170%`
   - Drenaje por segundo: `0.34% / s`
   - Pérdida acumulada en 3 minutos: **~61.2%** (Alerta naranja: el embalse entra en zona crítica).
3. **Ola de Calor Severa con 3 Fugas Abiertas (21.5 L/s, Multiplicador x1.85):**
   - Drenaje por tick: `(0.0035 + 21.5 * 0.0009) * 1.85 = 0.0423%`
   - Drenaje por segundo: `0.846% / s`
   - Pérdida durante los 18 segundos del evento: **~15.2% instantáneo**. Requiere respuesta inmediata.

---

## 3. Eventos Climáticos Dinámicos

Los eventos climáticos se activan periódicamente cada 600 ticks (30 segundos) de forma autoritativa en el servidor:

```mermaid
flowchart LR
    A["Tick 0s: Inicio"] --> B["Tick 30s: 🔥 Ola de Calor"]
    B --> C["Tick 60s: Fase de Estabilización"]
    C --> D["Tick 90s: 🌧️ Lluvia Torrencial"]
    D --> E["Tick 120s: 🔥 Segunda Ola de Calor"]
    E --> F["Tick 150s: Sprint Final"]
    F --> G["Tick 180s: 🏆 Fin de Partida"]
```

| Evento Climático | Multiplicador | Duración | Efecto en la Dinámica |
| :--- | :---: | :---: | :--- |
| **🔥 Ola de Calor (Heatwave)** | `x1.85` | `18 segundos` | La demanda comunal y la evaporación aumentan drásticamente. Las fugas abiertas aceleran la sequía. **Bonificación de +50 pts extra** por reparar tuberías bajo este estado. |
| **🌧️ Lluvia Torrencial (Rain Harvest)** | `x1.60` | `15 segundos` | Aporte pluvial de `0.040 * 1.6 = 0.064% por tick` (+1.28% de nivel por segundo). Permite recuperar hasta un **+19.2% de volumen** en el embalse si el equipo mantiene las válvulas hacia el huerto. |

---

## 4. Economía de Puntuación y Gamificación 3R

Cada acción ecológica está recompensada numéricamente y retroalimenta la tabla de clasificación (*Leaderboards*):

| Pilar Ecológico | Acción del Jugador | Litros Afectados | Puntos de Equipo | Puntos Individuales |
| :--- | :--- | :---: | :---: | :---: |
| **1. REDUCIR** | Sellar fuga de tubería con llave inglesa | `+75.0 L` ahorrados | `+150 pts` | `+150 pts` |
| **1. REDUCIR (Heroico)** | Sellar fuga en plena Ola de Calor activa | `+75.0 L` ahorrados | `+200 pts` | `+200 pts` |
| **2. REUSAR** | Desviar válvula hacia huertos comunitarios | `+20.0 L` reusados | `+50 pts` | `+50 pts` |
| **3. RECICLAR** | Filtrado biológico de lodos en planta | `+50.0 L` reciclados<br>*(+2.0% pureza)* | `+100 pts` | `+100 pts` |
| **🏆 BONO FINAL** | Supervivencia a los 180s con embalse > 0% | Retención remanente | `+ (Embalse% * 5)` | Asignado al equipo |

*Ejemplo de puntuación en partida victoria con 75% de embalse preservado y 8 fugas reparadas:*  
Puntos base: `8 * 150 = 1,200 pts` + `4 desvíos = 200 pts` + `2 reciclajes = 200 pts` + `Bono sostenibilidad = 75 * 5 = 375 pts`  
**Puntuación Final:** **1,975 puntos (Rango Maestro Sostenible 🌟)**.

---

## 5. Validación Anti-Cheat y Parámetros de Seguridad

Para garantizar un juego justo en partidas públicas en la nube, el motor de Rust valida autoritativamente cada movimiento e interacción:
- **Anti-Speedhack:** Desplazamiento máximo permitido por tick (50 ms): **`8.5 unidades`**. Todo salto mayor a 8.5 unidades es rechazado como intento de teletransporte o speedhack.
- **Rango de Reparación de Tubería:** Distancia Euclidiana máxima: **`18.0 unidades`**.
- **Rango de Operación de Válvulas:** Distancia máxima: **`20.0 unidades`**.
- **Rango de Mantenimiento de Planta:** Distancia máxima: **`28.0 unidades`**.

Con este conjunto de parámetros, EcoStream 3R garantiza una experiencia de juego balanceada, competitiva, pedagógica y robusta.
