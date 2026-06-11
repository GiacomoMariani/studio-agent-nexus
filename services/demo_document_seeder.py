from pathlib import Path

from services.document_ingestion_service import DocumentIngestionService
from services.pdf_parser import extract_pdf_pages


class DemoDocumentSeeder:
    def __init__(
        self,
        demo_dir: str,
        ingestion_service: DocumentIngestionService,
    ):
        self.demo_dir = Path(demo_dir)
        self.ingestion_service = ingestion_service

    async def seed(self) -> None:
        if not self.demo_dir.exists():
            return

        # All demo copies per filename — a plain filename->id dict would silently keep
        # only one id, leaving any accumulated duplicates in the store forever.
        existing_demo_ids: dict[str, list[str]] = {}
        for document in self.ingestion_service.store.list_documents():
            if document.is_demo:
                existing_demo_ids.setdefault(document.filename, []).append(
                    document.document_id
                )

        for path in sorted(self.demo_dir.iterdir()):
            if not path.is_file():
                continue

            if path.suffix.lower() not in {".txt", ".md", ".pdf"}:
                continue

            # README files document the demo folder; they are not knowledge-base content.
            if path.stem.lower() == "readme":
                continue

            # Re-seed from source each startup so demo docs always reflect the current
            # ingestion/chunking pipeline; drop every stale copy first (duplicates can
            # accumulate, e.g. from two processes seeding the same db). force=True
            # bypasses the store's demo-deletion guard (which blocks API/user deletes).
            for stale_document_id in existing_demo_ids.get(path.name, []):
                self.ingestion_service.store.delete_document(
                    stale_document_id, force=True
                )

            text = self._read_text(path)

            await self.ingestion_service.ingest_text(
                filename=path.name,
                text=text,
                is_demo=True,
            )

    def _read_text(self, path: Path) -> str:
        if path.suffix.lower() == ".pdf":
            pages = extract_pdf_pages(path.read_bytes())

            return "\n\n".join(
                f"[Page {page.page_number}]\n{page.text}"
                for page in pages
            )

        return path.read_text(encoding="utf-8")