"""API tests for the planning-suggestions endpoints (upsert + promote)."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

AUTH = {"X-API-Key": "test-secret-key"}

VALID = {
    "suggestion_id": "SUG-001",
    "title": "Document the PII purge window",
    "reason": "Pipeline stores PII events with no deletion policy.",
    "department": "Data",
    "priority": "Critical",
    "source": "data_pipeline_spec.pdf",
}


def test_post_creates_suggestion():
    response = client.post("/planning-suggestions", headers=AUTH, json=VALID)
    assert response.status_code == 200
    body = response.json()
    assert body["suggestion_id"] == "SUG-001"
    assert body["updated_at"]


def test_post_same_id_overwrites():
    client.post("/planning-suggestions", headers=AUTH, json=VALID)
    client.post("/planning-suggestions", headers=AUTH, json={**VALID, "priority": "High"})

    listing = client.get("/planning-suggestions", headers=AUTH).json()
    matching = [s for s in listing if s["suggestion_id"] == "SUG-001"]
    assert len(matching) == 1
    assert matching[0]["priority"] == "High"


def test_post_rejects_invalid_enum():
    payload = {**VALID, "priority": "Urgent"}
    response = client.post("/planning-suggestions", headers=AUTH, json=payload)
    assert response.status_code == 422


def test_list_returns_suggestions():
    client.post("/planning-suggestions", headers=AUTH, json=VALID)
    client.post("/planning-suggestions", headers=AUTH, json={**VALID, "suggestion_id": "SUG-002"})
    listing = client.get("/planning-suggestions", headers=AUTH).json()
    assert {s["suggestion_id"] for s in listing} == {"SUG-001", "SUG-002"}


def test_delete_suggestion():
    client.post("/planning-suggestions", headers=AUTH, json=VALID)
    deleted = client.delete("/planning-suggestions/SUG-001", headers=AUTH)
    assert deleted.status_code == 200
    assert deleted.json() == {"suggestion_id": "SUG-001", "deleted": True}


def test_delete_unknown_returns_404():
    assert client.delete("/planning-suggestions/SUG-404", headers=AUTH).status_code == 404


def test_schema_describes_contract():
    schema = client.get("/planning-suggestions/schema", headers=AUTH).json()
    assert schema["identity"] == "suggestion_id"
    departments = schema["fields"]["department"]["enum"]
    assert departments == ["Backend", "Infra", "Data", "QA", "Production"]
    assert schema["server_assigned"] == ["updated_at"]


def test_promote_creates_backlog_review_and_removes_suggestion():
    client.post("/planning-suggestions", headers=AUTH, json=VALID)

    promoted = client.post("/planning-suggestions/SUG-001/promote", headers=AUTH)
    assert promoted.status_code == 200

    review = promoted.json()
    assert review["task_id"] == "SUG-001"  # task_id == suggestion_id
    assert review["state"] == "backlog"
    assert review["description"] == VALID["reason"]

    # The review now appears in GET /reviews ...
    reviews = client.get("/reviews", headers=AUTH).json()
    assert any(r["task_id"] == "SUG-001" and r["state"] == "backlog" for r in reviews)

    # ... and the suggestion is gone.
    suggestions = client.get("/planning-suggestions", headers=AUTH).json()
    assert all(s["suggestion_id"] != "SUG-001" for s in suggestions)


def test_promote_unknown_returns_404():
    assert client.post("/planning-suggestions/SUG-404/promote", headers=AUTH).status_code == 404


def test_endpoints_require_api_key():
    assert client.post("/planning-suggestions", json=VALID).status_code == 401
    assert client.get("/planning-suggestions").status_code == 401
    assert client.get("/planning-suggestions/schema").status_code == 401
    assert client.delete("/planning-suggestions/SUG-001").status_code == 401
    assert client.post("/planning-suggestions/SUG-001/promote").status_code == 401
