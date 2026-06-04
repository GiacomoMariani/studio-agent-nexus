"""API tests for the reviews endpoints (upsert by task_id)."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

AUTH = {"X-API-Key": "test-secret-key"}

VALID = {
    "task_id": "TASK-001",
    "title": "Reconcile matchmaking SLA target",
    "description": "15s vs 10s.",
    "department": "Backend",
    "priority": "Critical",
    "source": "release_readiness_checklist.md",
    "state": "ai",
}


def test_post_creates_and_returns_record():
    response = client.post("/reviews", headers=AUTH, json=VALID)
    assert response.status_code == 200

    body = response.json()
    assert body["task_id"] == "TASK-001"
    assert body["updated_at"]
    assert "review_id" not in body
    assert body["state"] == "ai"


def test_post_same_task_id_overwrites():
    client.post("/reviews", headers=AUTH, json=VALID)
    client.post("/reviews", headers=AUTH, json={**VALID, "state": "done", "title": "Moved"})

    listing = client.get("/reviews", headers=AUTH).json()
    matching = [r for r in listing if r["task_id"] == "TASK-001"]
    assert len(matching) == 1  # overwritten, not duplicated
    assert matching[0]["state"] == "done"
    assert matching[0]["title"] == "Moved"


def test_list_returns_all_reviews():
    client.post("/reviews", headers=AUTH, json=VALID)
    client.post("/reviews", headers=AUTH, json={**VALID, "task_id": "TASK-002"})

    listing = client.get("/reviews", headers=AUTH).json()
    assert {r["task_id"] for r in listing} == {"TASK-001", "TASK-002"}


def test_post_rejects_invalid_department():
    response = client.post("/reviews", headers=AUTH, json={**VALID, "department": "Marketing"})
    assert response.status_code == 422


def test_post_rejects_invalid_state():
    response = client.post("/reviews", headers=AUTH, json={**VALID, "state": "shipped"})
    assert response.status_code == 422


def test_post_requires_title():
    payload = {**VALID}
    del payload["title"]
    assert client.post("/reviews", headers=AUTH, json=payload).status_code == 422


def test_delete_by_task_id():
    client.post("/reviews", headers=AUTH, json=VALID)
    deleted = client.delete("/reviews/TASK-001", headers=AUTH)
    assert deleted.status_code == 200
    assert deleted.json() == {"task_id": "TASK-001", "deleted": True}


def test_delete_unknown_returns_404():
    assert client.delete("/reviews/TASK-404", headers=AUTH).status_code == 404


def test_schema_describes_upsert_contract():
    schema = client.get("/reviews/schema", headers=AUTH).json()
    assert schema["identity"] == "task_id"
    fields = schema["fields"]
    assert fields["department"]["enum"] == ["Backend", "Infra", "Data", "QA", "Production"]
    assert fields["priority"]["enum"] == ["Critical", "High", "Medium", "Low"]
    assert fields["state"]["enum"] == ["ai", "lead", "backlog", "todo", "doing", "done"]
    assert schema["server_assigned"] == ["updated_at"]


def test_endpoints_require_api_key():
    assert client.post("/reviews", json=VALID).status_code == 401
    assert client.get("/reviews").status_code == 401
    assert client.get("/reviews/schema").status_code == 401
    assert client.delete("/reviews/TASK-001").status_code == 401
