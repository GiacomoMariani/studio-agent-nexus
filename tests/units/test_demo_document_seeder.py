"""Unit tests for DemoDocumentSeeder file selection.

Uses a fake ingestion service so no embeddings run.
"""

import pytest

from services.demo_document_seeder import DemoDocumentSeeder


class FakeStore:
    def list_documents(self):
        return []


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
async def test_seeder_skips_already_seeded(tmp_path):
    (tmp_path / "team_directory_and_ownership.md").write_text("# Team", encoding="utf-8")

    class SeededStore(FakeStore):
        def list_documents(self):
            class _Doc:
                filename = "team_directory_and_ownership.md"
                is_demo = True
            return [_Doc()]

    service = FakeIngestionService()
    service.store = SeededStore()
    seeder = DemoDocumentSeeder(demo_dir=str(tmp_path), ingestion_service=service)
    await seeder.seed()

    assert service.ingested == []
