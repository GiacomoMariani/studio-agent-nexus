# Sprint Delivery Plan — Game Title Online Beta

> Fictional demo document for Studio Agent Nexus. Synthetic content, safe for public use.

This plan sequences the work to reach the Game Title online beta milestone. It is the
production view of what is ready, what is in progress, and what each team is delivering.

## Milestone goal

Ship a stable online beta: authoritative servers on an autoscaling fleet, matchmaking
meeting the beta SLA, a lossless event pipeline feeding analytics, and verified cross-play
auth — with observability and on-call in place.

## Phase 1 — Foundation (in progress)

**Teams: Backend, Infra**

- Authoritative server build deployed to a staging fleet.
- Fleet allocator integrated with matchmaking.
- CI/CD pipeline promoting builds dev → staging → prod.

Dependency: staging environment must mirror production. **This is currently not provisioned
and is blocking load testing** (see Release Readiness Checklist).

## Phase 2 — Scale and data (in progress)

**Teams: Infra, Data**

- Autoscaling validated against a 2× peak-load test (blocked on staging).
- Event pipeline running end-to-end into the warehouse.
- Retention and monetization dashboards populated from live events.

Dependency: load testing requires the staging environment from Phase 1.

## Phase 3 — Readiness and tuning (not started)

**Teams: Backend, QA, Production**

- Matchmaking tuned to the beta SLA (p95 under 10 seconds).
- Full QA regression pass on the beta build.
- On-call rotation and runbooks finalised.
- Go-live sign-off against the readiness checklist.

Dependency: matchmaking SLA target must be reconciled — architecture currently targets
15 seconds while the readiness checklist requires 10 seconds.

## What is ready now

- Cross-play auth and identity linking (Backend) — verified.
- Event ingestion at expected volume (Data) — ready.

## What is at risk

- The whole milestone is gated by the unprovisioned staging environment.
- The matchmaking SLA conflict must be resolved before Phase 3 can close.
- Autoscaling has no documented maximum fleet ceiling, which blocks capacity sign-off.

## Owners

See the Team Directory for service owners. Production (Omar Haddad) owns milestone status
and sequencing; Infra (Sven Holt) owns the staging-environment blocker.
