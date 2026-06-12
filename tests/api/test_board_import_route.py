"""API tests for POST /admin/board/import — bulk board replace (ticket-019).

Replace semantics per entity key: present ⇒ erase-then-insert the whole set, absent ⇒
untouched, empty list ⇒ cleared. The payload is validated before anything is erased, and
the import must never touch document data.
"""

from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)
AUTH = {"X-API-Key": "test-secret-key"}

REVIEW = {
    "task_id": "TASK-100",
    "title": "Reconcile authoritative server tick rate",
    "description": "30 Hz vs 60 Hz.",
    "department": "Backend",
    "priority": "Critical",
    "source": "backend_architecture_overview.md",
    "state": "ai",
}

SUGGESTION = {
    "suggestion_id": "SUG-100",
    "title": "Add SLA alerting thresholds for matchmaking",
    "reason": "No alerting on p95 breaches.",
    "department": "Backend",
    "priority": "High",
    "source": "backend_architecture_overview.md",
}

RISK = {
    "risk_id": "RISK-100",
    "kind": "risk",
    "severity": "Critical",
    "title": "Autoscaling maximum fleet size is undocumented",
    "description": "No hard ceiling for autoscaling.",
    "source": "server_fleet_runbook.pdf",
}


def _seed_target_state():
    """Pre-existing target content that a replace must erase."""
    client.post(
        "/reviews",
        headers=AUTH,
        json={**REVIEW, "task_id": "REMOTE-1", "title": "Old remote task"},
    )
    client.post(
        "/planning-suggestions",
        headers=AUTH,
        json={**SUGGESTION, "suggestion_id": "REMOTE-SUG-1"},
    )
    client.post("/risks", headers=AUTH, json={**RISK, "risk_id": "REMOTE-RISK-1"})


def test_import_replaces_all_three_entity_sets():
    _seed_target_state()

    response = client.post(
        "/admin/board/import",
        headers=AUTH,
        json={
            "reviews": [REVIEW, {**REVIEW, "task_id": "TASK-101", "state": "done"}],
            "planning_suggestions": [SUGGESTION],
            "risks": [RISK],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reviews"] == {"deleted": 1, "imported": 2}
    assert body["planning_suggestions"] == {"deleted": 1, "imported": 1}
    assert body["risks"] == {"deleted": 1, "imported": 1}

    reviews = client.get("/reviews", headers=AUTH).json()
    assert {r["task_id"] for r in reviews} == {"TASK-100", "TASK-101"}
    suggestions = client.get("/planning-suggestions", headers=AUTH).json()
    assert {s["suggestion_id"] for s in suggestions} == {"SUG-100"}
    risks = client.get("/risks", headers=AUTH).json()
    assert {r["risk_id"] for r in risks} == {"RISK-100"}


def test_absent_key_leaves_that_entity_set_untouched():
    _seed_target_state()

    response = client.post(
        "/admin/board/import",
        headers=AUTH,
        json={"reviews": [REVIEW]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reviews"] == {"deleted": 1, "imported": 1}
    assert body["planning_suggestions"] is None
    assert body["risks"] is None

    suggestions = client.get("/planning-suggestions", headers=AUTH).json()
    assert {s["suggestion_id"] for s in suggestions} == {"REMOTE-SUG-1"}
    risks = client.get("/risks", headers=AUTH).json()
    assert {r["risk_id"] for r in risks} == {"REMOTE-RISK-1"}


def test_empty_list_clears_that_entity_set():
    _seed_target_state()

    response = client.post("/admin/board/import", headers=AUTH, json={"risks": []})

    assert response.status_code == 200
    assert response.json()["risks"] == {"deleted": 1, "imported": 0}
    assert client.get("/risks", headers=AUTH).json() == []
    # The other two sets were absent from the body — untouched.
    assert len(client.get("/reviews", headers=AUTH).json()) == 1
    assert len(client.get("/planning-suggestions", headers=AUTH).json()) == 1


def test_one_invalid_item_rejects_the_whole_import_and_erases_nothing():
    _seed_target_state()

    response = client.post(
        "/admin/board/import",
        headers=AUTH,
        json={
            "reviews": [REVIEW, {**REVIEW, "task_id": "TASK-101", "department": "Marketing"}],
            "risks": [RISK],
        },
    )

    assert response.status_code == 422
    reviews = client.get("/reviews", headers=AUTH).json()
    assert {r["task_id"] for r in reviews} == {"REMOTE-1"}
    risks = client.get("/risks", headers=AUTH).json()
    assert {r["risk_id"] for r in risks} == {"REMOTE-RISK-1"}


def test_import_does_not_touch_documents_or_chunks():
    document = main.sqlite_document_store.save_document(
        filename="guide.md",
        text="# Guide\nFastAPI is the framework.",
        chunk_payloads=[{"text": "FastAPI is the framework.", "embedding": [0.1, 0.2]}],
        is_demo=True,
    )

    response = client.post(
        "/admin/board/import",
        headers=AUTH,
        json={"reviews": [REVIEW], "planning_suggestions": [], "risks": []},
    )
    assert response.status_code == 200

    documents = client.get("/documents", headers=AUTH).json()["documents"]
    assert [d["document_id"] for d in documents] == [document.document_id]
    assert documents[0]["chunk_count"] == 1
    content = client.get(f"/documents/{document.document_id}/content", headers=AUTH).json()
    assert content["content"] == "# Guide\nFastAPI is the framework."


def test_duplicate_ids_in_one_payload_collapse_via_upsert():
    response = client.post(
        "/admin/board/import",
        headers=AUTH,
        json={"reviews": [REVIEW, {**REVIEW, "title": "Second write wins"}]},
    )

    assert response.status_code == 200
    assert response.json()["reviews"] == {"deleted": 0, "imported": 1}
    reviews = client.get("/reviews", headers=AUTH).json()
    assert len(reviews) == 1
    assert reviews[0]["title"] == "Second write wins"


def test_import_requires_api_key():
    assert client.post("/admin/board/import", json={"reviews": []}).status_code == 401
    assert (
        client.post(
            "/admin/board/import",
            headers={"X-API-Key": "wrong-key"},
            json={"reviews": []},
        ).status_code
        == 401
    )
