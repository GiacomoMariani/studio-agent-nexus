"""API tests for POST /documents/ask/task-suggestions (ticket-018).

Rule mode + a fake embedder keep this offline and fast (zero LLM tokens, no model load). The
route is ephemeral — it must persist nothing.
"""

from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)
AUTH = {"X-API-Key": "test-secret-key"}


class FakeEmbeddingProvider:
    def _vec(self, text: str) -> list[float]:
        lowered = text.lower()
        if "matchmaking" in lowered:
            return [1.0, 0.0, 0.0]
        if "purge" in lowered or "pii" in lowered:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)

    def embed_document(self, text: str) -> list[float]:
        return self._vec(text)


def _seed_review():
    main.sqlite_review_store.upsert(
        task_id="R1", title="Matchmaking SLA mismatch", description="p95",
        department="Backend", priority="High", source="a.md", state="backlog",
    )


def test_requires_api_key():
    response = client.post("/documents/ask/task-suggestions", json={"question": "x"})
    assert response.status_code == 401


def test_empty_question_rejected():
    response = client.post("/documents/ask/task-suggestions", headers=AUTH, json={"question": ""})
    assert response.status_code == 422


def test_returns_related_and_suggested(monkeypatch):
    monkeypatch.setattr(main, "embedding_provider", FakeEmbeddingProvider())
    _seed_review()

    body = {
        "question": "How does matchmaking work?",
        "answer": "The deployment runbook has not been provisioned.",
    }
    response = client.post("/documents/ask/task-suggestions", headers=AUTH, json=body)

    assert response.status_code == 200
    data = response.json()
    assert any(r["task_id"] == "R1" for r in data["related"])
    assert data["suggested"]  # the 'not been provisioned' cue yields a draft (rule generator)
    assert all("draft_id" in draft for draft in data["suggested"])


def test_persists_nothing(monkeypatch):
    monkeypatch.setattr(main, "embedding_provider", FakeEmbeddingProvider())
    _seed_review()

    client.post(
        "/documents/ask/task-suggestions", headers=AUTH,
        json={"question": "matchmaking", "answer": "The purge window is not specified."},
    )

    # Only the seeded review exists — no new reviews / suggestions / risks were written.
    assert {r["task_id"] for r in client.get("/reviews", headers=AUTH).json()} == {"R1"}
    assert client.get("/planning-suggestions", headers=AUTH).json() == []
    assert client.get("/risks", headers=AUTH).json() == []


def test_generator_error_returns_500(monkeypatch):
    monkeypatch.setattr(main, "embedding_provider", FakeEmbeddingProvider())

    class _Boom:
        async def generate(self, documents):
            from services.exceptions import AppServiceError

            raise AppServiceError("kaboom")

    monkeypatch.setattr(main, "get_jira_task_generator", lambda settings: _Boom())

    response = client.post(
        "/documents/ask/task-suggestions", headers=AUTH,
        json={"question": "matchmaking", "answer": "x"},
    )
    assert response.status_code == 500
    assert "kaboom" in response.json()["detail"]
