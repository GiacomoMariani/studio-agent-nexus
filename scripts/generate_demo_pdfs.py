"""Generate the demo PDF documents for Studio Agent Nexus.

Dev-time content tool (not a runtime dependency — the app only reads PDFs via pypdf).
Requires reportlab (in requirements-dev.txt). Run from the project root:

    python scripts/generate_demo_pdfs.py

Produces three fictional, backend/production-themed PDFs under demo/. All content is
synthetic and safe for public demonstration. Embedded conflicts (mirrored in
frontend/fixtures.py) let the agent demo contradiction + risk detection.
"""

from __future__ import annotations

import os

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

DEMO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo")

_styles = getSampleStyleSheet()
_BODY = ParagraphStyle(
    "Body", parent=_styles["Normal"], fontSize=10.5, leading=15, spaceAfter=8,
)
_H1 = ParagraphStyle(
    "H1", parent=_styles["Title"], fontSize=20, leading=24, spaceAfter=12, alignment=TA_LEFT,
)
_H2 = ParagraphStyle(
    "H2", parent=_styles["Heading2"], fontSize=13, leading=17, spaceBefore=10, spaceAfter=6,
)
_NOTE = ParagraphStyle(
    "Note", parent=_BODY, textColor="#64748B", fontSize=9, leading=13,
)


def _bullets(items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(t, _BODY), leftIndent=10) for t in items],
        bulletType="bullet",
        start="•",
        leftIndent=14,
    )


def _build(filename: str, blocks: list) -> None:
    path = os.path.join(DEMO_DIR, filename)
    doc = SimpleDocTemplate(
        path, pagesize=letter,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.9 * inch, bottomMargin=0.9 * inch,
        title=filename,
    )
    doc.build(blocks)
    print(f"Wrote {path}")


# ---------------------------------------------------------------------------
# 2. Server Fleet Runbook
# ---------------------------------------------------------------------------
def server_fleet_runbook() -> None:
    s: list = [
        Paragraph("Server Fleet Runbook — Game Title", _H1),
        Paragraph(
            "Fictional demo document for Studio Agent Nexus. Synthetic content, safe for "
            "public demonstration. Operational runbook for the dedicated game-server fleet "
            "that hosts Game Title matches at Game Studio.", _NOTE),
        Spacer(1, 8),

        Paragraph("1. Purpose", _H2),
        Paragraph(
            "This runbook covers how the dedicated game-server fleet is operated: regions, "
            "allocation, autoscaling, deployment, rollback, and on-call response. It is the "
            "operational companion to the Backend Architecture Overview.", _BODY),

        Paragraph("2. Fleet topology", _H2),
        Paragraph(
            "Game Title runs dedicated server instances grouped into regional pools. Each "
            "match is hosted on exactly one instance, allocated on demand when matchmaking "
            "forms a match. Instances are stateless beyond the lifetime of the match they "
            "host.", _BODY),
        _bullets([
            "Regions: NA-East, NA-West, EU-Central, and AP-Southeast.",
            "Each region maintains a warm pool of pre-booted instances to absorb demand "
            "spikes without cold-start latency.",
            "An allocator service hands a ready instance to matchmaking on request and "
            "marks it busy for the match duration.",
        ]),

        Paragraph("3. Capacity and sizing", _H2),
        Paragraph(
            "Per-instance capacity is derived from the simulation cost. For sizing, the "
            "fleet model assumes each server instance runs the simulation at 60 Hz and "
            "budgets CPU headroom accordingly. Instance counts per region are scaled from "
            "expected concurrent matches at peak.", _BODY),
        Paragraph(
            "Note: capacity numbers must be reconciled with the authoritative tick rate "
            "stated in the Backend Architecture Overview before the load test.", _NOTE),

        Paragraph("4. Autoscaling", _H2),
        Paragraph(
            "The fleet autoscales on warm-pool depletion and queued-allocation pressure. "
            "When the warm pool falls below a regional threshold, the allocator requests "
            "additional instances; idle instances above the threshold are drained after a "
            "cooldown.", _BODY),
        _bullets([
            "Scale-up trigger: warm pool below regional minimum for 60 seconds.",
            "Scale-down trigger: warm pool above regional maximum for 5 minutes.",
            "Scale-up step and cooldown are tuned per region.",
        ]),
        Paragraph(
            "Open gap: the maximum fleet size is not defined. There is currently no hard "
            "upper bound on how many instances autoscaling may request, so capacity "
            "planning, cost ceilings, and saturation alerts cannot be set. This must be "
            "resolved before the beta load test.", _BODY),

        Paragraph("5. Deployment", _H2),
        Paragraph(
            "Server builds are promoted dev → staging → prod through the CI/CD pipeline. "
            "Deploys are rolling: new instances boot the new build into the warm pool while "
            "in-flight matches drain on the old build. No live match is interrupted by a "
            "deploy.", _BODY),

        Paragraph("6. Rollback", _H2),
        Paragraph(
            "If a bad build is detected, the allocator is pinned to the last-known-good "
            "build and new instances boot from it. Instances on the bad build are drained "
            "as their matches end. Rollback does not evict live matches.", _BODY),

        Paragraph("7. On-call response", _H2),
        _bullets([
            "Capacity alert (warm pool exhausted): verify autoscaling is firing; manually "
            "raise regional minimums if demand exceeds the model.",
            "Allocation failures: check allocator health and regional instance supply.",
            "Bad build: trigger rollback and notify the incident commander.",
        ]),
        Paragraph(
            "Primary on-call for the fleet is the Infra owner listed in the Team Directory. "
            "Severity calls and external communication are owned by the incident commander.",
            _BODY),
    ]
    _build("server_fleet_runbook.pdf", s)


# ---------------------------------------------------------------------------
# 3. Data Pipeline Spec
# ---------------------------------------------------------------------------
def data_pipeline_spec() -> None:
    s: list = [
        Paragraph("Data Pipeline Specification — Game Title", _H1),
        Paragraph(
            "Fictional demo document for Studio Agent Nexus. Synthetic content, safe for "
            "public demonstration. Specifies how gameplay and platform events are ingested, "
            "processed, and stored for analytics at Game Studio.", _NOTE),
        Spacer(1, 8),

        Paragraph("1. Purpose", _H2),
        Paragraph(
            "This spec defines the event pipeline that carries telemetry from game servers "
            "and platform services into the analytics warehouse. The pipeline is "
            "asynchronous and never sits on the gameplay hot path.", _BODY),

        Paragraph("2. Event flow", _H2),
        Paragraph(
            "Producers (game servers and services) publish events to a message bus. "
            "Stream processors validate, enrich, and route events into warehouse tables. "
            "Consumers include analytics, live-ops tooling, and anti-cheat.", _BODY),
        _bullets([
            "Transport: a partitioned message bus with per-domain topics.",
            "Topics: match_events, economy_events, auth_events, session_events, ad_events.",
            "Delivery: at-least-once; consumers are idempotent on event_id.",
        ]),

        Paragraph("3. Event schema", _H2),
        Paragraph(
            "Every event shares an envelope: event_id, event_type, player_id, session_id, "
            "server_id, timestamp (UTC), schema_version, and a typed payload. Schemas are "
            "versioned; breaking changes require a new schema_version and a migration note.",
            _BODY),

        Paragraph("4. Sampling and volume", _H2),
        Paragraph(
            "High-frequency gameplay signals are sampled before publication to keep volume "
            "bounded; low-frequency lifecycle events (match start/end, purchases, logins) "
            "are always published. Sampling rates are managed through live config.", _BODY),

        Paragraph("5. Warehouse and retention", _H2),
        Paragraph(
            "Validated events land in the analytics warehouse, partitioned by event_type "
            "and date. Retention windows are defined per table. Daily metrics are bucketed "
            "by UTC calendar day; for example, D1 retention is computed against the next "
            "calendar day after install, not a rolling 24-hour window.", _BODY),
        Paragraph(
            "Open gap: the retention and purge window for player-identifying (PII) event "
            "fields is not specified. Until a compliance decision sets an explicit purge "
            "window, PII-bearing events accumulate without a defined deletion policy.",
            _BODY),

        Paragraph("6. Quality and monitoring", _H2),
        _bullets([
            "Schema validation rejects malformed events to a dead-letter topic.",
            "Ingestion lag and dead-letter volume are dashboarded and alerted.",
            "Lossless ingestion at expected volume is a beta go-live criterion.",
        ]),

        Paragraph("7. Access", _H2),
        Paragraph(
            "Analytics consumers read curated warehouse tables, not raw topics. Raw topic "
            "access is restricted to the Data team. Ownership is recorded in the Team "
            "Directory.", _BODY),
    ]
    _build("data_pipeline_spec.pdf", s)


# ---------------------------------------------------------------------------
# 7. Player Analytics and Metrics
# ---------------------------------------------------------------------------
def player_analytics_and_metrics() -> None:
    s: list = [
        Paragraph("Player Analytics and Metrics — Game Title", _H1),
        Paragraph(
            "Fictional demo document for Studio Agent Nexus. Synthetic content, safe for "
            "public demonstration. Defines the player-facing metrics tracked for Game Title: "
            "analytics funnels, authentication, retention, and monetization/ads.", _NOTE),
        Spacer(1, 8),

        Paragraph("1. Purpose", _H2),
        Paragraph(
            "This document defines how Game Studio measures player behaviour for Game Title "
            "and how those metrics are computed from the event pipeline. It is the reference "
            "for the analytics and monetization dashboards.", _BODY),

        Paragraph("2. Core engagement metrics", _H2),
        _bullets([
            "DAU / MAU: distinct players with at least one session in the day / month.",
            "Sessions per player and average session length.",
            "Concurrency: peak and average concurrent players, by region.",
        ]),

        Paragraph("3. Authentication and login funnel", _H2),
        Paragraph(
            "The login funnel measures conversion from launch to authenticated session: "
            "launch → account selection → credential validation → session established. "
            "Drop-off at each step is tracked from auth_events. Cross-play identity linking "
            "is measured as the share of accounts with more than one linked platform.", _BODY),

        Paragraph("4. Retention", _H2),
        Paragraph(
            "Retention measures whether players return after install. D1 retention counts a "
            "player as retained if they return within 24 hours of install — a rolling "
            "24-hour window from the install timestamp. D7 and D30 follow the same rolling "
            "definition from install.", _BODY),
        Paragraph(
            "Note: this rolling-window definition differs from the calendar-day bucketing "
            "described in the Data Pipeline Spec, and the two must be reconciled so "
            "dashboards agree.", _NOTE),

        Paragraph("5. Monetization and ads", _H2),
        Paragraph(
            "Monetization combines in-app purchases (IAP) and rewarded/interstitial ads.", _BODY),
        _bullets([
            "ARPU and ARPPU across IAP and ad revenue.",
            "IAP conversion: share of players making at least one purchase.",
            "Ad metrics: impressions, fill rate, eCPM, and ad ARPU.",
        ]),
        Paragraph(
            "Open gap: ad revenue metrics depend on a player consent flag that is not yet "
            "wired through the client SDK. Until the consent signal is captured and joined "
            "to ad_events, ad fill rate and ad ARPU are under-reported and the data cannot "
            "be considered privacy-compliant for regions that require consent.", _BODY),

        Paragraph("6. Dashboards", _H2),
        _bullets([
            "Engagement: DAU/MAU, sessions, concurrency.",
            "Acquisition & auth: install-to-session funnel, link rate.",
            "Retention: D1/D7/D30 cohorts.",
            "Monetization: IAP, ads, ARPU — populating live events is a beta criterion.",
        ]),

        Paragraph("7. Ownership", _H2),
        Paragraph(
            "Analytics and metrics are owned by the Data team (see the Team Directory). "
            "Pipeline questions route to the event-pipeline owner; metric-definition "
            "questions route to the analytics owner.", _BODY),
    ]
    _build("player_analytics_and_metrics.pdf", s)


def main() -> None:
    server_fleet_runbook()
    data_pipeline_spec()
    player_analytics_and_metrics()


if __name__ == "__main__":
    main()
