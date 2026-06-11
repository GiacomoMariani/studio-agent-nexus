"""Unit tests for DemoDocumentSeeder file selection.

Uses a fake ingestion service so no embeddings run.
"""

import pytest

from services.demo_document_seeder import DemoDocumentSeeder


class FakeStore:
    def __init__(self):
        self.deleted: list[str] = []
        # Maps document_id -> is_demo, so the fake can mirror the real store's
        # guard: demo docs are only deletable when the caller passes force=True.
        self.demo_ids: set[str] = set()

    def list_documents(self):
        return []

    def delete_document(self, document_id: str, *, force: bool = False) -> bool:
        if document_id in self.demo_ids and not force:
            return False

        self.deleted.append(document_id)
        return True


class FakeIngestionService:
    def __init__(self):
        self.store = FakeStore()
        self.ingested: list[str] = []

    async def ingest_text(self, filename: str, text: str, is_demo: bool):
        self.ingested.append(filename)


@pytest.mark.asyncio
async def test_seeder_skips_readme_and_non_supported(tmp_path):
    (tmp_path / "backend_architecture_overview.md").write_text("# Arch\nbody", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("plain notes", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Demo readme\nmeta docs", encoding="utf-8")
    (tmp_path / "diagram.png").write_bytes(b"\x89PNG not-real")

    service = FakeIngestionService()
    seeder = DemoDocumentSeeder(demo_dir=str(tmp_path), ingestion_service=service)
    await seeder.seed()

    assert "backend_architecture_overview.md" in service.ingested
    assert "notes.txt" in service.ingested
    assert "README.md" not in service.ingested  # README is documentation, not content
    assert "diagram.png" not in service.ingested  # unsupported type
    assert len(service.ingested) == 2


@pytest.mark.asyncio
async def test_seeder_replaces_already_seeded(tmp_path):
    (tmp_path / "team_directory_and_ownership.md").write_text("# Team", encoding="utf-8")

    class SeededStore(FakeStore):
        def __init__(self):
            super().__init__()
            # The existing copy is a demo doc, so the store guards it against
            # deletion unless the seeder explicitly forces it.
            self.demo_ids.add("doc-existing")

        def list_documents(self):
            class _Doc:
                document_id = "doc-existing"
                filename = "team_directory_and_ownership.md"
                is_demo = True

            return [_Doc()]

    service = FakeIngestionService()
    service.store = SeededStore()
    seeder = DemoDocumentSeeder(demo_dir=str(tmp_path), ingestion_service=service)
    await seeder.seed()

    # The stale copy is dropped (force-deleting past the demo guard) and the doc is
    # re-ingested with the current pipeline. A non-forced delete would no-op here,
    # leaving `deleted` empty — which is the duplication bug this guards against.
    assert service.store.deleted == ["doc-existing"]
    assert service.ingested == ["team_directory_and_ownership.md"]


@pytest.mark.asyncio
async def test_seeder_deletes_all_duplicate_demo_copies(tmp_path):
    (tmp_path / "backend_architecture_overview.md").write_text("# Arch", encoding="utf-8")

    class DuplicatedStore(FakeStore):
        def __init__(self):
            super().__init__()
            self.demo_ids.update({"doc-1", "doc-2", "doc-3"})

        def list_documents(self):
            class _Doc:
                filename = "backend_architecture_overview.md"
                is_demo = True

                def __init__(self, document_id):
                    self.document_id = document_id

            return [_Doc("doc-1"), _Doc("doc-2"), _Doc("doc-3")]

    service = FakeIngestionService()
    service.store = DuplicatedStore()
    seeder = DemoDocumentSeeder(demo_dir=str(tmp_path), ingestion_service=service)
    await seeder.seed()

    # Every accumulated copy is dropped — not just the last one listed — and the
    # doc is re-ingested exactly once.
    assert sorted(service.store.deleted) == ["doc-1", "doc-2", "doc-3"]
    assert service.ingested == ["backend_architecture_overview.md"]
