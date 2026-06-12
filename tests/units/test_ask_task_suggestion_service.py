"""AskTaskSuggestionService combines related matches + deduped suggestions (ticket-018)."""

import pytest

from models.jira_task import JiraTaskDraft
from services.ask_task_suggestion_service import AskTaskSuggestionService
from services.related_task_service import RelatedTaskService


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


class StubGenerator:
    def __init__(self, drafts):
        self._drafts = drafts
        self.seen_docs = None

    async def generate(self, documents):
        self.seen_docs = list(documents)
        return self._drafts


class StubStore:
    def __init__(self, rows):
        self._rows = rows

    def list(self):
        return self._rows


MATCH_DRAFT = JiraTaskDraft(
    draft_id="d-mm", issue_type="Task", summary="Improve matchmaking latency",
    priority="High", department="Backend", source="Ask page",
)
NEW_DRAFT = JiraTaskDraft(
    draft_id="d-pii", issue_type="Story", summary="Define PII purge window",
    priority="High", department="Data", source="Ask page",
)


def _service(*, reviews=(), suggestions=(), generator=None, suggest_max=8, min_score=0.5):
    return AskTaskSuggestionService(
        review_store=StubStore(list(reviews)),
        suggestion_store=StubStore(list(suggestions)),
        related_service=RelatedTaskService(
            embedding_provider=FakeEmbeddingProvider(), min_score=min_score
        ),
        generator=generator,
        suggest_max=suggest_max,
    )


@pytest.mark.asyncio
async def test_returns_related_and_dedupes_suggestions():
    reviews = [{"task_id": "R1", "title": "Matchmaking SLA", "description": "",
                "department": "Backend", "priority": "High", "source": "a"}]
    generator = StubGenerator([MATCH_DRAFT, NEW_DRAFT])
    service = _service(reviews=reviews, generator=generator)

    result = await service.suggest(question="How does matchmaking work?", answer="")

    assert [r.task_id for r in result["related"]] == ["R1"]
    # MATCH_DRAFT duplicates the related 'Matchmaking SLA' task → dropped; NEW_DRAFT kept.
    assert [d.draft_id for d in result["suggested"]] == ["d-pii"]
    # Generator seeded with a single synthetic 'Ask page' document.
    assert [d.filename for d in generator.seen_docs] == ["Ask page"]


@pytest.mark.asyncio
async def test_blank_question_skips_generator():
    generator = StubGenerator([NEW_DRAFT])
    service = _service(generator=generator)

    result = await service.suggest(question="   ", answer="ignored")

    assert result == {"related": [], "suggested": []}
    assert generator.seen_docs is None  # generator never called


@pytest.mark.asyncio
async def test_suggest_max_caps_results():
    drafts = [
        JiraTaskDraft(draft_id=f"d-{i}", issue_type="Task", summary=f"unrelated thing {i}",
                      priority="Low", department="QA", source="Ask page")
        for i in range(10)
    ]
    service = _service(generator=StubGenerator(drafts), suggest_max=3)

    result = await service.suggest(question="matchmaking", answer="")

    assert result["related"] == []  # no board items
    assert len(result["suggested"]) == 3
