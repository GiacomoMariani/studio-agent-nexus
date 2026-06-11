from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class StoredChunk:
    chunk_id: str
    text: str
    embedding: list[float]
    page_number: int | None = None


@dataclass(frozen=True)
class StoredDocumentSummary:
    document_id: str
    filename: str
    file_type: str
    upload_date: str
    status: str
    page_count: int | None
    chunk_count: int
    is_demo: bool = False


@dataclass(frozen=True)
class StoredDocument:
    document_id: str
    filename: str
    original_text: str
    file_type: str
    upload_date: str
    status: str
    page_count: int | None
    chunks: list[StoredChunk] = field(default_factory=list)
    is_demo: bool = False


class InMemoryDocumentStore:
    def __init__(self):
        self._documents: dict[str, StoredDocument] = {}

    def save_document(
        self,
        filename: str,
        text: str,
        chunk_payloads: list[dict[str, object]],
        is_demo: bool = False,
    ) -> StoredDocument:
        document_id = f"doc-{uuid4().hex[:12]}"
        page_count = self._infer_page_count(chunk_payloads)

        chunks = [
            StoredChunk(
                chunk_id=f"{document_id}-chunk-{index + 1}",
                text=str(chunk_payload["text"]),
                embedding=chunk_payload["embedding"],
                page_number=chunk_payload.get("page_number"),
            )
            for index, chunk_payload in enumerate(chunk_payloads)
        ]

        stored_document = StoredDocument(
            document_id=document_id,
            filename=filename,
            original_text=text,
            file_type=self._infer_file_type(filename),
            upload_date=self._now(),
            status="indexed",
            page_count=page_count,
            chunks=chunks,
            is_demo=is_demo,
        )

        self._documents[document_id] = stored_document
        return stored_document

    def get_document(self, document_id: str) -> StoredDocument | None:
        return self._documents.get(document_id)

    def list_documents(self) -> list[StoredDocumentSummary]:
        return [
            StoredDocumentSummary(
                document_id=document.document_id,
                filename=document.filename,
                file_type=document.file_type,
                upload_date=document.upload_date,
                status=document.status,
                page_count=document.page_count,
                chunk_count=len(document.chunks),
                is_demo=document.is_demo,
            )
            for document in self._documents.values()
        ]

    def delete_document(self, document_id: str, *, force: bool = False) -> bool:
        document = self._documents.get(document_id)

        if document is None:
            return False

        # Demo docs are protected from API/user deletion; only trusted internal
        # callers (the seeder re-seeding from source) pass force=True to drop them.
        if document.is_demo and not force:
            return False

        del self._documents[document_id]
        return True

    def replace_document_chunks(
        self,
        document_id: str,
        chunk_payloads: list[dict[str, object]],
    ) -> StoredDocument | None:
        stored_document = self.get_document(document_id)

        if stored_document is None:
            return None

        chunks = [
            StoredChunk(
                chunk_id=f"{document_id}-chunk-{index + 1}",
                text=str(chunk_payload["text"]),
                embedding=chunk_payload["embedding"],
                page_number=chunk_payload.get("page_number"),
            )
            for index, chunk_payload in enumerate(chunk_payloads)
        ]

        updated_document = StoredDocument(
            document_id=stored_document.document_id,
            filename=stored_document.filename,
            original_text=stored_document.original_text,
            file_type=stored_document.file_type,
            upload_date=stored_document.upload_date,
            status="indexed",
            page_count=self._infer_page_count(chunk_payloads),
            chunks=chunks,
            is_demo=stored_document.is_demo,
        )

        self._documents[document_id] = updated_document
        return updated_document

    def clear(self) -> None:
        self._documents.clear()

    def _infer_file_type(self, filename: str) -> str:
        suffix = Path(filename).suffix.lower().lstrip(".")

        if suffix:
            return suffix

        return "unknown"

    def _infer_page_count(
        self,
        chunk_payloads: list[dict[str, object]],
    ) -> int | None:
        page_numbers = [
            int(chunk_payload["page_number"])
            for chunk_payload in chunk_payloads
            if chunk_payload.get("page_number") is not None
        ]

        if not page_numbers:
            return None

        return max(page_numbers)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()


document_store = InMemoryDocumentStore()