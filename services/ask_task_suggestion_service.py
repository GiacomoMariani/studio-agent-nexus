"""Ask-page actionable answers: related existing tasks + suggested new drafts (ticket-018).

Composes the two halves and **writes nothing** (drafts are ephemeral):
  - **related**  — `RelatedTaskService` ranks the board's reviews + planning-suggestions against
    the question with local embeddings (zero LLM tokens).
  - **suggested** — reuses the ticket-017 `JiraTaskGenerator`, seeded by the question + answer
    wrapped as a single synthetic document, then drops any draft already covered by a related
    existing task (the "double-check, then only suggest what's new" step).
"""

from __future__ import annotations

from types import SimpleNamespace

from models.ask_tasks import RelatedTask
from models.jira_task import JiraTaskDraft
from services.jira_task_generator import JiraTaskGenerator
from services.related_task_service import RelatedTaskService

# A draft this close to an already-tracked task is treated as a duplicate and dropped.
_DEDUP_MIN_SIMILARITY = 0.6
_SEED_FILENAME = "Ask page"


class _Store:  # structural: review/suggestion stores both expose .list()
    def list(self) -> list[dict]: ...


class AskTaskSuggestionService:
    def __init__(
        self,
        *,
        review_store: _Store,
        suggestion_store: _Store,
        related_service: RelatedTaskService,
        generator: JiraTaskGenerator,
        suggest_max: int = 8,
    ) -> None:
        self._review_store = review_store
        self._suggestion_store = suggestion_store
        self._related_service = related_service
        self._generator = generator
        self._suggest_max = suggest_max

    async def suggest(self, *, question: str, answer: str = "") -> dict:
        query = question.strip()
        if not query:
            return {"related": [], "suggested": []}

        related = self._related_service.match(query, self._board_items())

        seed = SimpleNamespace(
            filename=_SEED_FILENAME,
            original_text=f"{question}\n\n{answer}".strip(),
        )
        drafts = await self._generator.generate([seed])
        suggested = self._dedup(drafts, related)[: self._suggest_max]

        return {"related": related, "suggested": suggested}

    def _board_items(self) -> list[dict]:
        items: list[dict] = []
        for review in self._review_store.list():
            items.append(
                {
                    "kind": "review",
                    "task_id": review["task_id"],
                    "title": review["title"],
                    "text": review.get("description", ""),
                    "department": review["department"],
                    "priority": review["priority"],
                    "source": review.get("source", ""),
                }
            )
        for suggestion in self._suggestion_store.list():
            items.append(
                {
                    "kind": "suggestion",
                    "task_id": suggestion["suggestion_id"],
                    "title": suggestion["title"],
                    "text": suggestion.get("reason", ""),
                    "department": suggestion["department"],
                    "priority": suggestion["priority"],
                    "source": suggestion.get("source", ""),
                }
            )
        return items

    def _dedup(
        self, drafts: list[JiraTaskDraft], related: list[RelatedTask]
    ) -> list[JiraTaskDraft]:
        related_titles = [task.title for task in related]
        if not related_titles:
            return list(drafts)
        return [
            draft
            for draft in drafts
            if self._related_service.max_similarity(draft.summary, related_titles)
            < _DEDUP_MIN_SIMILARITY
        ]
