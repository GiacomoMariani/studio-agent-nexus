# Release Readiness Checklist — Game Title Online Beta

> Fictional demo document for Studio Agent Nexus. Synthetic content, safe for public use.

This checklist defines the go-live criteria for the Game Title online beta milestone at
Game Studio. A criterion is "Ready" only when its owning team has signed off against the
evidence listed.

## Go-live criteria

| Area | Criterion | Status | Owner |
|------|-----------|--------|-------|
| Matchmaking | **p95 matchmaking time must be under 10 seconds** at beta concurrency | Not ready | Backend |
| Server fleet | Autoscaling validated against a 2× expected-peak load | Blocked | Infra |
| Data pipeline | Event ingestion lossless at expected event volume | Ready | Data |
| Auth | Cross-play identity linking verified on all platforms | Ready | Backend |
| Observability | Dashboards + alerts cover fleet, matchmaking, and ingestion | In progress | Infra |
| Analytics | Retention and monetization dashboards populated from live events | In progress | Data |
| QA | Full regression pass on the beta build | In progress | QA |

## Blockers

- **Load testing is blocked.** The staging environment that mirrors production has not been
  provisioned, so we cannot run the 2× peak-load test required to validate fleet
  autoscaling. This is the critical-path blocker for the milestone.
- **Matchmaking SLA gap.** The go-live SLA requires **matchmaking p95 under 10 seconds**,
  but the current architecture target is 15 seconds. Backend and Production must reconcile
  the target before sign-off.

## Deliverables for this milestone

- Authoritative server build deployed to the staging fleet.
- Matchmaking service tuned to the beta SLA.
- Event pipeline running end-to-end into the analytics warehouse.
- Cross-play auth verified.
- On-call rotation and runbooks in place for beta.

## Sign-off

Release is approved only when every go-live criterion is "Ready" and both blockers are
cleared. Current overall status: **NOT READY** — pending staging provisioning and the
matchmaking SLA decision.
