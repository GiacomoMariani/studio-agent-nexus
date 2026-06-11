"""API tests for POST /admin/jira-tasks/generate (ticket-017).

Runs in rule mode (conftest forces JIRA_TASK_GENERATOR_TYPE=rule, keys scrubbed), so this
spends zero tokens. Drafts are ephemeral — the route must persist nothing.
"""

from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)
AUTH = {"X-API-Key": "test-secret-key"}

DOCS = {
    "backend_architecture_overview.md": (
        "The authoritative simulation runs at 30 Hz. The matchmaking retry policy is not "
        "specified and must be defined before launch."
    ),
    "server_fleet_runbook.pdf": (
        "There is currently no hard upper bound on how many instances autoscaling may request. "
        "The staging environment that mirrors production has not been provisioned."
    ),
}


def _seed(docs=DOCS):
    for filename, text in docs.items():
        main.sqlite_document_store.save_document(
            filename=filename, text=text, chunk_payloads=[], is_demo=True,
        )


def test_requires_api_key():
    assert client.post("/admin/jira-tasks/generate", json={}).status_code == 401


def test_generates_drafts_for_all_documents():
    _seed()
    response = client.post("/admin/jira-tasks/generate", headers=AUTH, json={})

    assert response.status_code == 200
    drafts = response.json()
    assert len(drafts) >= 1
    first = drafts[0]
    assert {"draft_id", "issue_type", "summary", "priority", "department", "source"} <= set(first)
    assert first["issue_type"] in {"Story", "Task", "Bug", "Epic"}


def test_scope_by_document_id_limits_source():
    _seed()
    document = main.sqlite_document_store.list_documents()[0]

    response = client.post(
        "/admin/jira-tasks/generate", headers=AUTH, json={"document_id": document.document_id}
    )

    assert response.status_code == 200
    drafts = response.json()
    assert drafts
    assert {d["source"] for d in drafts} == {document.filename}


def test_unknown_document_id_returns_empty():
    _seed()
    response = client.post(
        "/admin/jira-tasks/generate", headers=AUTH, json={"document_id": "doc-nope"}
    )
    assert response.status_code == 200
    assert response.json() == []


def test_generation_persists_nothing():
    _seed()
    client.post("/admin/jira-tasks/generate", headers=AUTH, json={})

    # Ephemeral: no planning-suggestions, reviews, or risks were created.
    assert client.get("/planning-suggestions", headers=AUTH).json() == []
    assert client.get("/reviews", headers=AUTH).json() == []
    assert client.get("/risks", headers=AUTH).json() == []


def test_generator_error_returns_500(monkeypatch):
    class _Boom:
        async def generate(self, documents):
            from services.exceptions import AppServiceError

            raise AppServiceError("kaboom")

    monkeypatch.setattr(main, "get_jira_task_generator", lambda settings: _Boom())
    _seed()

    response = client.post("/admin/jira-tasks/generate", headers=AUTH, json={})
    assert response.status_code == 500
    assert "kaboom" in response.json()["detail"]
