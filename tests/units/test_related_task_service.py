"""RelatedTaskService ranks board tasks by embedding similarity (ticket-018).

Uses a controllable fake embedder for deterministic ranking/floor tests, plus one check with
the real local sentence-transformer for semantic sanity. All offline, zero LLM tokens.
"""

import pytest

from providers.embedding_provider import LocalEmbeddingProvider
from services.related_task_service import RelatedTaskService


class FakeEmbeddingProvider:
    """Maps text to a unit vector by topic keyword, so cosine is deterministic."""

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


ITEMS = [
    {"kind": "review", "task_id": "R1", "title": "Matchmaking SLA mismatch",
     "text": "p95 15s vs 10s", "department": "Backend", "priority": "High", "source": "a.md"},
    {"kind": "suggestion", "task_id": "S1", "title": "Define PII purge window",
     "text": "retention", "department": "Data", "priority": "High", "source": "b.pdf"},
    {"kind": "review", "task_id": "R2", "title": "Office snacks",
     "text": "kitchen", "department": "Production", "priority": "Low", "source": ""},
]


def test_matches_related_above_floor_and_ranks():
    service = RelatedTaskService(embedding_provider=FakeEmbeddingProvider(), min_score=0.5, top_n=5)
    related = service.match("How does matchmaking work?", ITEMS)

    assert [r.task_id for r in related] == ["R1"]  # only matchmaking clears the 0.5 floor
    assert related[0].kind == "review"
    assert related[0].score == pytest.approx(1.0)


def test_top_n_caps_results():
    items = [
        {"kind": "review", "task_id": f"R{i}", "title": "matchmaking", "text": "",
         "department": "Backend", "priority": "High", "source": ""}
        for i in range(5)
    ]
    service = RelatedTaskService(embedding_provider=FakeEmbeddingProvider(), min_score=0.5, top_n=2)
    assert len(service.match("matchmaking", items)) == 2


def test_below_floor_excluded():
    service = RelatedTaskService(embedding_provider=FakeEmbeddingProvider(), min_score=0.5, top_n=5)
    # A query about snacks (→ [0,0,1]) is orthogonal to the matchmaking/purge items → none match.
    assert service.match("office snacks please", [ITEMS[0], ITEMS[1]]) == []


def test_no_items_returns_empty():
    service = RelatedTaskService(embedding_provider=FakeEmbeddingProvider())
    assert service.match("matchmaking", []) == []


def test_blank_query_returns_empty():
    service = RelatedTaskService(embedding_provider=FakeEmbeddingProvider())
    assert service.match("   ", ITEMS) == []


def test_max_similarity_for_dedup():
    service = RelatedTaskService(embedding_provider=FakeEmbeddingProvider())
    assert service.max_similarity("matchmaking draft", ["Matchmaking SLA"]) == pytest.approx(1.0)
    assert service.max_similarity("matchmaking draft", ["Office snacks"]) == pytest.approx(0.0)
    assert service.max_similarity("anything", []) == 0.0


def test_real_embedder_ranks_semantically():
    service = RelatedTaskService(
        embedding_provider=LocalEmbeddingProvider(), min_score=0.2, top_n=3
    )
    items = [
        {"kind": "review", "task_id": "MM", "title": "Matchmaking latency SLA",
         "text": "p95 under 10 seconds", "department": "Backend",
         "priority": "High", "source": "x"},
        {"kind": "suggestion", "task_id": "SNACK", "title": "Restock office snacks",
         "text": "kitchen supplies", "department": "Production",
         "priority": "Low", "source": "y"},
    ]
    related = service.match("How fast is matchmaking?", items)

    assert related and related[0].task_id == "MM"
