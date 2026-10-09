# Project: EcoStream-3R — Technical Branch Comparison (`Side-dev` vs `fase1`)

## Architecture
Comparative assessment of Cloud Computing systems architectures:
- **Control Plane**: Go Gateway (gRPC :50051 & HTTP REST :8080) handling Auth (JWT/bcrypt), Matchmaking, Room reservation, Worker pool with drop telemetry, and Cache-Aside (Redis 7 + PostgreSQL fallback).
- **Data Plane**: Rust Engine running an authoritative 20 Hz Tokio simulation loop (50 ms ticks), autonomous HMAC-SHA256 room ticket verification, physics/anti-cheat validation (normalized directional intent, proximity-bounded 3R mechanics), and decoupled chat broadcast channels.
- **Protobuf Contracts**: `ecostream.v1` unified interface contracts (`auth.proto`, `matchmaking.proto`, `gameplay.proto`, `common.proto`, `internal.proto`).
- **Clients**: Desktop client in TypeScript/Tauri with Canvas 2D and bot/testing client in Python with Pygame (available in `fase1`), compared to the backend-hardened state in `Side-dev`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Architecture & Control Plane | Dual exposure (gRPC & HTTP), stateless Gateway, worker pool, graceful shutdown | M1 / M2 | Explorer 1 |
| 2 | Data Plane & Simulation Loop | 20 Hz loop, authoritative simulation, decoupled chat stream, RTT Ping-Pong | M1 / M2 | Explorer 1 |
| 3 | Protobuf Contracts & gRPC | `ecostream.v1` contracts, MoveAction normalized vectors, internal coordinator RPCs | M1 / M2 | Explorer 1 |
| 4 | Authentication & Security | Bcrypt hashing, elimination of `SuperEcoPass123!`, HMAC-SHA256 Room Tickets, JWT HS256 | M1 / M2 | Explorer 2 |
| 5 | Anti-Cheat & Authoritative Physics | Directional intent, $\Delta t$ bounds, clamp boundaries, $\le 65.0$ px 3R interaction radius | M1 / M2 | Explorer 2 |
| 6 | Persistence, Concurrency & Caching | Atomic `UPDATE ... WHERE < max_players`, DDL constraints, Redis Cache-Aside & soft fallback | M1 / M2 | Explorer 2 |
| 7 | Bounded Queues & Telemetry | Non-blocking `select-default` channels, atomic `dropped_events`, `/readyz` metrics | M1 / M2 | Explorer 2 |
| 8 | Client Layer & Presentation | Evaluation of Tauri Canvas 2D and Python Pygame clients in `fase1` vs `Side-dev` status | M1 / M2 | Explorer 3 |
| 9 | Observability & Automated Tests | Unit/Integration test suites (100% pass), `/healthz`, `/readyz`, `/api/v1/stats/metrics` | M1 / M2 | Explorer 3 |
| 10 | Documentation & UML Models | 6 Mermaid diagrams (Deployment, Use Case, Components, Sequence, Circuit Breaker, State) | M1 / M2 | Explorer 3 |
| 11 | Academic Context & 3Rs Design | Educational water conservation mechanics (Reduce, Reuse, Recycle) and university fit | M1 / M2 | Explorer 3 |
| 12 | Roadmap & Rescue Strategy | Step-by-step migration plan to adapt `fase1` clients to `Side-dev` secure contracts | M1 / M2 | Explorer 3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Survey & Technical Exploration | Deep inspection of git refs, codebases, tests, and documentation | none | DONE |
| M2 | Comparison Report Drafting | Full generation of `COMPARACION_SIDE_DEV_VS_FASE1.md` with tables and snippets | M1 | DONE |
| M3 | Review, Challenge & Forensic Audit | Independent review (x2), empirical challenges (x2), and integrity audit | M2 | DONE |
| M4 | Gate & Final Delivery | Final synthesis, acceptance verification, and handoff to parent | M3 | DONE |

## Interface Contracts
- **Go Gateway ↔ Client**: gRPC :50051 & HTTP :8080 (REST + CORS).
- **Go Gateway ↔ Rust Engine**: Internal gRPC `ProvisionRoom(room_id, max_players)` and `NotifyMatchFinished(room_id, metrics)`.
- **Client ↔ Rust Engine**: Direct streaming over gRPC `StreamGame(GameStreamRequest)` verified autonomously via HMAC-SHA256 `room_ticket`. Chat over `StreamChat`.
- **Gateway ↔ Redis 7 / PostgreSQL**: Cache-Aside with 30s TTL on room status; atomic SQL updates for concurrency.

## Code Layout
- `COMPARACION_SIDE_DEV_VS_FASE1.md`: Definitive technical comparative report at workspace root (675 lines).
- `gateway-go/`: Go Control Plane (cmd/server, internal/auth, internal/matchmaking, internal/storage, internal/workerpool).
- `engine-rust/`: Rust Data Plane (src/game, src/service, src/auth, tests/).
- `proto/`: Protobuf definitions (`ecostream/v1/`).
- `deployments/`: Docker Compose, PostgreSQL schemas, Redis configurations.
- `docs/`: Architectural specifications, UML diagrams, decisions, test plans.
