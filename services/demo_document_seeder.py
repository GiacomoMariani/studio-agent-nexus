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

        existing_filenames = {
            document.filename
            for document in self.ingestion_service.store.list_documents()
            if document.is_demo
        }

        for path in sorted(self.demo_dir.iterdir()):
            if not path.is_file():
                continue

            if path.name in existing_filenames:
                continue

            if path.suffix.lower() not in {".txt", ".md", ".pdf"}:
                continue

            # README files document the demo folder; they are not knowledge-base content.
            if path.stem.lower() == "readme":
                continue

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