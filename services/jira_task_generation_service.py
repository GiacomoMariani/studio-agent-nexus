"""Jira-task generation orchestration: load documents → generate drafts → return (ticket-017).

Unlike `RiskDetectionService`, this writes **nothing** — drafts are ephemeral. Scope is a
single `document_id` or, when None, every distinct document (collapsed by filename so the
demo's duplicate seed rows don't multiply the drafts). When the scope resolves to no
documents the generator is skipped and an empty list is returned.
"""

from __future__ import annotations

from models.jira_task import JiraTaskDraft
from services.jira_task_generator import JiraTaskGenerator
from services.sqlite_document_store import SQLiteDocumentStore


class JiraTaskGenerationService:
    def __init__(
        self,
        *,
        document_store: SQLiteDocumentStore,
        generator: JiraTaskGenerator,
    ) -> None:
        self._document_store = document_store
        self._generator = generator

    async def generate(self, document_id: str | None = None) -> list[JiraTaskDraft]:
        documents = self._load_documents(document_id)
        if not documents:
            return []
        return await self._generator.generate(documents)

    def _load_documents(self, document_id: str | None) -> list:
        if document_id is not None:
            document = self._document_store.get_document(document_id)
            return [document] if document is not None else []

        # All documents: one `StoredDocument` per filename (collapse duplicate demo rows).
        distinct: dict[str, object] = {}
        for summary in self._document_store.list_documents():
            if summary.filename in distinct:
                continue
            document = self._document_store.get_document(summary.document_id)
            if document is not None:
                distinct[summary.filename] = document
        return list(distinct.values())
