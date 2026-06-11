"""Jira-task generation — generator abstraction + fallback wrapper (ticket-017).

Mirrors the risk-detection design (`services/risk_detector.py`): a `Protocol` over a
sequence of documents returning Jira-shaped task drafts, plus a `FallbackJiraTaskGenerator`
that drops from the LLM path to the rule-based one on `AppServiceError`. The unit of currency
is the Pydantic `JiraTaskDraft` directly — there is no persistence layer to map through, so
no separate dataclass is needed (the one real difference from the risk pattern).
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from models.jira_task import JiraTaskDraft
from services.exceptions import AppServiceError


@runtime_checkable
class SourceDocument(Protocol):
    """The slice of a stored document a generator reads. `StoredDocument` satisfies this."""

    filename: str
    original_text: str


class JiraTaskGenerator(Protocol):
    async def generate(self, documents: Sequence[SourceDocument]) -> list[JiraTaskDraft]: ...


class FallbackJiraTaskGenerator:
    """Run the primary generator; on `AppServiceError`, fall back to the secondary one.

    Mirrors `FallbackRiskDetector`: a misconfigured or failing LLM path degrades to the
    deterministic rule-based generator instead of turning a request into a 500.
    """

    def __init__(self, *, primary: JiraTaskGenerator, fallback: JiraTaskGenerator) -> None:
        self._primary = primary
        self._fallback = fallback

    async def generate(self, documents: Sequence[SourceDocument]) -> list[JiraTaskDraft]:
        try:
            return await self._primary.generate(documents)
        except AppServiceError:
            return await self._fallback.generate(documents)
