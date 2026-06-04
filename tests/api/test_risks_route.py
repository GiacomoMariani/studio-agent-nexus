"""API tests for the risks endpoints (upsert; risk + contradiction kinds)."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

AUTH = {"X-API-Key": "test-secret-key"}

RISK = {
    "risk_id": "RISK-001",
    "kind": "risk",
    "severity": "Critical",
    "title": "Autoscaling max fleet size is undocumented",
    "description": "No hard ceiling for autoscaling.",
    "source": "server_fleet_runbook.pdf",
}

CONTRADICTION = {
    "risk_id": "RISK-002",
    "kind": "contradiction",
    "severity": "High",
    "title": "Conflicting server tick rate",
    "a_file": "backend_architecture_overview.md",
    "a_text": "30 Hz",
    "b_file": "server_fleet_runbook.pdf",
    "b_text": "60 Hz",
}


def test_post_creates_risk():
    body = client.post("/risks", headers=AUTH, json=RISK).json()
    assert body["risk_id"] == "RISK-001"
    assert body["kind"] == "risk"
    assert body["updated_at"]


def test_post_creates_contradiction():
    body = client.post("/risks", headers=AUTH, json=CONTRADICTION).json()
    assert body["kind"] == "contradiction"
    assert body["a_file"] == "backend_architecture_overview.md"
    assert body["b_text"] == "60 Hz"


def test_post_same_id_overwrites():
    client.post("/risks", headers=AUTH, json=RISK)
    client.post("/risks", headers=AUTH, json={**RISK, "severity": "Low"})
    findings = client.get("/risks", headers=AUTH).json()
    matching = [f for f in findings if f["risk_id"] == "RISK-001"]
    assert len(matching) == 1
    assert matching[0]["severity"] == "Low"


def test_post_rejects_invalid_kind():
    assert client.post("/risks", headers=AUTH, json={**RISK, "kind": "bug"}).status_code == 422


def test_post_rejects_invalid_severity():
    payload = {**RISK, "severity": "Urgent"}
    assert client.post("/risks", headers=AUTH, json=payload).status_code == 422


def test_list_returns_findings():
    client.post("/risks", headers=AUTH, json=RISK)
    client.post("/risks", headers=AUTH, json=CONTRADICTION)
    findings = client.get("/risks", headers=AUTH).json()
    assert {f["risk_id"] for f in findings} == {"RISK-001", "RISK-002"}


def test_delete_ok_and_404():
    client.post("/risks", headers=AUTH, json=RISK)
    assert client.delete("/risks/RISK-001", headers=AUTH).status_code == 200
    assert client.delete("/risks/RISK-001", headers=AUTH).status_code == 404


def test_schema_describes_contract():
    schema = client.get("/risks/schema", headers=AUTH).json()
    assert schema["identity"] == "risk_id"
    assert schema["fields"]["kind"]["enum"] == ["risk", "contradiction"]
    assert schema["fields"]["severity"]["enum"] == ["Critical", "High", "Medium", "Low"]
    assert schema["server_assigned"] == ["updated_at"]


def test_endpoints_require_api_key():
    assert client.post("/risks", json=RISK).status_code == 401
    assert client.get("/risks").status_code == 401
    assert client.get("/risks/schema").status_code == 401
    assert client.delete("/risks/RISK-001").status_code == 401
