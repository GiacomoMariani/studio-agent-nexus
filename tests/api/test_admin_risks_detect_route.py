"""API tests for POST /admin/risks/detect (ticket-011).

The detector runs in rule mode (conftest forces RISK_DETECTOR_TYPE=rule, keys scrubbed), so
this spends zero tokens. Demo docs are seeded into the per-test store with the planted
evidence text, so the rule detector surfaces all seven findings.
"""

import main
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
AUTH = {"X-API-Key": "test-secret-key"}

DEMO_DOCS = {
    "backend_architecture_overview.md": (
        "Simulation tick rate: the authoritative simulation runs at 30 Hz (one tick every "
        "33 ms). The target matchmaking time is p95 under 15 seconds at expected concurrency."
    ),
    "server_fleet_runbook.pdf": (
        "For sizing, the fleet model assumes each server instance runs the simulation at 60 Hz. "
        "There is currently no hard upper bound on how many instances autoscaling may request."
    ),
    "data_pipeline_spec.pdf": (
        "Daily metrics are bucketed by UTC calendar day; for example, D1 retention is computed "
        "against the next calendar day after install, not a rolling 24-hour window. "
        "The purge window for player-identifying (PII) event fields is not specified."
    ),
    "player_analytics_and_metrics.pdf": (
        "D1 retention counts a player as retained if they return within a rolling 24-hour "
        "window from the install timestamp. Ad revenue metrics depend on a player consent flag "
        "that is not yet wired through the client SDK."
    ),
    "release_readiness_checklist.md": (
        "The go-live SLA requires matchmaking p95 under 10 seconds, but the current "
        "architecture target is 15 seconds. The staging environment that mirrors production "
        "has not been provisioned."
    ),
}


def _seed_demo_docs():
    for filename, text in DEMO_DOCS.items():
        main.sqlite_document_store.save_document(
            filename=filename, text=text, chunk_payloads=[], is_demo=True,
        )


def test_requires_api_key():
    assert client.post("/admin/risks/detect").status_code == 401


def test_detects_seven_findings_and_exposes_them_via_get_risks():
    _seed_demo_docs()

    response = client.post("/admin/risks/detect", headers=AUTH)
    assert response.status_code == 200
    assert len(response.json()) == 7

    listed = client.get("/risks", headers=AUTH).json()
    auto = [r for r in listed if r["risk_id"].startswith("auto-")]
    assert len(auto) == 7
    assert {r["kind"] for r in auto} == {"risk", "contradiction"}


def test_rerun_is_idempotent():
    _seed_demo_docs()
    client.post("/admin/risks/detect", headers=AUTH)
    client.post("/admin/risks/detect", headers=AUTH)

    auto = [r for r in client.get("/risks", headers=AUTH).json() if r["risk_id"].startswith("auto-")]
    assert len(auto) == 7


def test_scan_preserves_hand_posted_risk():
    _seed_demo_docs()
    client.post("/risks", headers=AUTH, json={
        "risk_id": "RISK-MANUAL", "kind": "risk", "severity": "High",
        "title": "Hand posted", "description": "keep me", "source": "x.md",
    })

    client.post("/admin/risks/detect", headers=AUTH)

    ids = {r["risk_id"] for r in client.get("/risks", headers=AUTH).json()}
    assert "RISK-MANUAL" in ids
    assert len([r for r in ids if r.startswith("auto-")]) == 7


def test_detector_error_returns_500(monkeypatch):
    class _Boom:
        async def detect(self, documents):
            from services.exceptions import AppServiceError
            raise AppServiceError("kaboom")

    monkeypatch.setattr(main, "get_risk_detector", lambda settings: _Boom())

    response = client.post("/admin/risks/detect", headers=AUTH)
    assert response.status_code == 500
    assert "kaboom" in response.json()["detail"]
