"""JiraTaskGenerationService scopes documents and returns drafts without persisting (ticket-017)."""

from types import SimpleNamespace

import pytest

from models.jira_task import JiraTaskDraft
from services.jira_task_generation_service import JiraTaskGenerationService


class StubGenerator:
    def __init__(self, drafts):
        self._drafts = drafts
        self.documents = None

    async def generate(self, documents):
        self.documents = list(documents)
        return self._drafts


class StubDocStore:
    def __init__(self, summaries=(), docs=None):
        self._summaries = list(summaries)
        self._docs = docs or {}
        self.fetched = []

    def list_documents(self):
        return self._summaries

    def get_document(self, document_id):
        self.fetched.append(document_id)
        return self._docs.get(document_id)


DRAFT = JiraTaskDraft(
    draft_id="draft-x", issue_type="Task", summary="Do X",
    priority="Medium", department="Backend", source="a.md",
)


@pytest.mark.asyncio
async def test_all_documents_collapsed_by_filename():
    summaries = [
        SimpleNamespace(filename="a.md", document_id="d1"),
        SimpleNamespace(filename="a.md", document_id="d2"),  # duplicate row
        SimpleNamespace(filename="b.md", document_id="d3"),
    ]
    docs = {
        "d1": SimpleNamespace(filename="a.md", original_text="A"),
        "d3": SimpleNamespace(filename="b.md", original_text="B"),
    }
    store = StubDocStore(summaries, docs)
    generator = StubGenerator([DRAFT])

    service = JiraTaskGenerationService(document_store=store, generator=generator)
    result = await service.generate(None)

    assert store.fetched == ["d1", "d3"]  # first per filename; duplicate skipped
    assert [d.filename for d in generator.documents] == ["a.md", "b.md"]
    assert result == [DRAFT]


@pytest.mark.asyncio
async def test_single_document_scope():
    docs = {"d1": SimpleNamespace(filename="a.md", original_text="A")}
    store = StubDocStore(summaries=[], docs=docs)
    generator = StubGenerator([DRAFT])

    service = JiraTaskGenerationService(document_store=store, generator=generator)
    await service.generate("d1")

    assert store.fetched == ["d1"]
    assert [d.filename for d in generator.documents] == ["a.md"]


@pytest.mark.asyncio
async def test_unknown_document_returns_empty_and_skips_generator():
    store = StubDocStore(summaries=[], docs={})
    generator = StubGenerator([DRAFT])

    service = JiraTaskGenerationService(document_store=store, generator=generator)

    assert await service.generate("missing") == []
    assert generator.documents is None  # generator not called when scope is empty
