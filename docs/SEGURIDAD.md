# Seguridad e Integridad de Datos: EcoStream 3R

> **Cátedra:** Computación en la Nube (UCAB - Ingeniería en Informática)
> Resumen de los riesgos que **sí** se mitigan en el proyecto y de los que quedan como trabajo futuro. El alcance general está en [ALCANCE_Y_DECISIONES.md](ALCANCE_Y_DECISIONES.md).

---

## 1. Principios

1. **Cero confianza en el cliente:** el cliente envía **intenciones** (hacia dónde quiere moverse, qué quiere reparar); el servidor Rust decide qué ocurre.
2. **Sin secretos en el código:** toda clave o contraseña se inyecta por variable de entorno; no existen valores por defecto ni contraseñas fijas.
3. **Defensa en capas:** transporte → identidad → reglas del servidor → integridad de datos.

---

## 2. Riesgos Dentro de Alcance

| # | Riesgo | Componente | Escenario de ataque | Mitigación |
| :-: | :--- | :--- | :--- | :--- |
| 1 | Credenciales o secretos por defecto | Go Gateway, `docker-compose` | Un atacante usa una contraseña fija o el secreto JWT publicado en el repositorio para firmar tokens o entrar a cualquier cuenta. | Secretos solo por variable de entorno, sin valores por defecto; sin contraseñas fijas en el login. |
| 2 | Conexión al motor sin identidad | Rust Engine | Un cliente abre el stream con cualquier `room_id` y `player_id` y se une (o crea) salas ajenas. | Rust valida la firma HMAC y la expiración del `RoomTicket` antes de aceptar el primer mensaje. |
| 3 | Teletransporte y velocidad imposible | Rust Engine | El cliente envía una posición arbitraria o movimientos más rápidos de lo permitido. | `MoveAction` es un vector de intención: Rust lo normaliza, limita la velocidad máxima por tick y recorta al mapa. |
| 4 | Acciones a distancia o en ráfaga | Rust Engine | El cliente repara una tubería lejana o envía miles de acciones por segundo. | Validación de proximidad (≤ 1,5 tiles), enfriamientos y límite de acciones por segundo por conexión. |
| 5 | Sobrecupo de sala | Go Gateway, PostgreSQL | Dos jugadores se unen a la vez al último puesto desde gateways distintos. | `UPDATE rooms SET current_players = current_players + 1 WHERE code = $1 AND current_players < max_players` y se verifica las filas afectadas. |
| 6 | Robo o filtrado del token de sesión | Clientes Tauri y Python, Go Gateway | El JWT viaja en el cuerpo de la petición o se guarda en `LocalStorage` y es leído por un script malicioso. | JWT en la cabecera `Authorization`; en Tauri se guarda en el almacenamiento seguro del sistema, no en `LocalStorage`. |
| 7 | Contraseñas expuestas | Go Gateway, PostgreSQL | Una filtración de la base revela contraseñas, o se capturan en tránsito. | Hash con bcrypt en el servidor; TLS en producción. |
| 8 | Mensajes sobredimensionados o inundación | Go Gateway, Rust Engine | Un cliente envía mensajes gigantes o abre cientos de streams para agotar memoria. | Límite de tamaño de mensaje gRPC y de conexiones/streams por cliente. |
| 9 | Pérdida silenciosa de historial | Go Worker Pool, PostgreSQL | Con Postgres caído, la cola se llena y los resultados de partida se descartan sin dejar rastro. | Cola acotada con reintento y backoff, contador de eventos descartados expuesto en `/readyz` y vaciado al apagar. |

---

## 3. Trabajo Futuro (Fuera de Alcance)

| Tema | Por qué se difiere |
| :--- | :--- |
| mTLS entre Go, Rust, Redis y PostgreSQL | En desarrollo basta una red Docker privada. |
| Autenticación y TLS en Redis | Redis solo guarda una caché de salas; no hay datos sensibles. |
| Cola durable de eventos (Redis Streams) | Se acepta una pérdida acotada y medida (riesgo 9). |
| Snapshots de partida y failover de Rust | Una caída de Rust termina la partida (decisión D3). |
| Defensa contra ataques HTTP/2 a nivel de red (Rapid Reset, Slowloris) | Corresponde a la infraestructura de producción. |
| Rotación de claves y lista de revocación de tickets | El ticket vive 60 s; el impacto es bajo. |

---

## 4. Nota de Método

El análisis de seguridad detallado (41 vectores) se realizó **sobre los documentos de diseño, no sobre el código**, así que no sustituye una prueba contra la implementación. Los incumplimientos concretos detectados en la rama `fase1` están en [ALCANCE_Y_DECISIONES.md](ALCANCE_Y_DECISIONES.md#4-desviaciones-conocidas-respecto-a-la-rama-fase1).
