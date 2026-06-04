# Backend Architecture Overview — Game Title

> Fictional demo document for Studio Agent Nexus. All names, numbers, and services are
> synthetic and safe for public demonstration. This describes the multiplayer backend for
> the working title "Game Title" at the fictional "Game Studio".

## 1. Purpose

This document is the single reference for how the Game Title online backend is structured:
the authoritative game servers, the matchmaking and session services, the player-facing
platform services, and the data stores behind them. It is written for engineers joining
the backend, infra, and data teams, and for producers who need to reason about delivery
and risk.

## 2. High-level topology

Game Title runs a client–server model with **authoritative dedicated game servers**. No
gameplay outcome is trusted from the client; the server simulates the match and the client
renders an approximation corrected by server state.

The backend is split into three planes:

- **Game plane** — dedicated server instances that run live matches.
- **Service plane** — stateless platform services (auth, matchmaking, sessions, profiles,
  inventory, live config) behind an API gateway.
- **Data plane** — the event pipeline, operational databases, cache, and the analytics
  warehouse.

Clients talk to the service plane over HTTPS/gRPC through the gateway. Once matched, a
client connects directly to an allocated game server over UDP.

## 3. Authoritative server model

Each match is hosted on a dedicated server instance allocated from the fleet (see the
Server Fleet Runbook). The server owns the simulation and is the source of truth for all
gameplay state.

- **Simulation tick rate: the authoritative simulation runs at 30 Hz (one tick every
  33 ms).** All gameplay systems — movement, hit detection, ability resolution — advance
  on this fixed tick.
- State is replicated to clients via delta snapshots. Each client receives the subset of
  world state relevant to it (interest management) to keep bandwidth bounded.
- Client input is sampled locally, sent to the server, and applied on the next authoritative
  tick. The client runs prediction locally and reconciles against authoritative snapshots.
- **Lag compensation**: the server rewinds recent state by the acknowledged client RTT when
  resolving time-critical interactions, bounded to a maximum rewind window.

Because the simulation is fixed at 30 Hz, the per-tick server CPU budget is 33 ms. Systems
that cannot complete inside that budget must be amortised across ticks or moved off the hot
path.

## 4. Matchmaking service

Matchmaking groups players into balanced matches and requests a server allocation for each
formed match.

- Players enter a queue keyed by playlist and region.
- The matcher widens the acceptable skill band over time to trade match quality for wait
  time.
- **The target matchmaking time is p95 under 15 seconds** at expected concurrency. When the
  queue cannot fill a match inside the widening window, players are offered a backfill or a
  bot-filled match depending on playlist rules.
- On match formation, the matchmaker calls the fleet allocator for a ready server instance
  in the chosen region and hands the connection details to all clients.

Matchmaking is stateless beyond the queue; queue state lives in the cache tier so any
matchmaker instance can serve any request.

## 5. Sessions, lobby, and party

- **Sessions** track an authenticated player's current connection, presence, and active
  match. Session tokens are short-lived and refreshed against the auth service.
- **Lobby/party** lets players group before queueing. A party enters matchmaking as a unit
  and is allocated to the same server.
- Presence (online/in-match/away) is published to friends through the social service.

## 6. Player accounts and authentication

- **Auth service** issues signed session tokens after validating platform credentials
  (console, PC store, or studio account). Tokens are JWT-style, short-lived, and refreshed.
- **Identity linking** lets one player join multiple platform identities to a single Game
  Studio account, enabling cross-play and cross-progression.
- Sensitive credential exchange never passes through game servers; only validated session
  tokens reach the service plane.

## 7. Service mesh and APIs

- All client-facing traffic enters through an **API gateway** that handles TLS termination,
  authentication, and rate limiting.
- Internal service-to-service calls use gRPC with mutual TLS.
- Public/edge endpoints are REST/JSON for broad client compatibility.
- Each service is stateless and horizontally scalable; shared state lives in the data plane.

## 8. Data stores

- **Operational SQL** (relational) for accounts, entitlements, and inventory — anything that
  needs transactional integrity.
- **Document store** for profile blobs and flexible per-player configuration.
- **Cache tier (Redis-style)** for sessions, matchmaking queues, presence, and hot reads.
- **Analytics warehouse** for telemetry, fed asynchronously by the event pipeline (see the
  Data Pipeline Spec). The warehouse is never on the gameplay hot path.

## 9. Message bus and events

Gameplay and service events are published to a message bus and consumed asynchronously by
the data pipeline, live-ops tooling, and anti-cheat. Producers do not block on consumers.
The bus decouples the game and service planes from analytics and back-office processing.

## 10. Latency and performance budgets

- Authoritative tick budget: **33 ms per tick (30 Hz)**.
- Target end-to-end input-to-render latency under good network conditions: under 100 ms.
- Matchmaking target: **p95 under 15 s** (see §4).
- Gateway added overhead budget: under 5 ms p50 per request.

## 11. Live configuration

A live-config service distributes feature flags and tunable values to clients and servers
without a redeploy, enabling staged rollouts and A/B experiments. Config changes are
versioned and auditable.

## 12. Security and anti-cheat

- The authoritative model is the first line of defence: clients cannot assert outcomes.
- Anti-cheat consumes server and telemetry events to detect anomalies.
- Rate limiting and token validation at the gateway protect platform services.

## 13. Open questions and known gaps

- The maximum server fleet size under autoscaling is not yet pinned down in the Fleet
  Runbook; capacity planning and alerting need a hard ceiling.
- Retention windows for player-identifying event data are not specified in the Data Pipeline
  Spec and need a compliance decision.
