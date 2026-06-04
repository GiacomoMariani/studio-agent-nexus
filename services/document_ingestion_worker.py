import logging

from services.document_ingestion_service import DocumentIngestionService
from services.exceptions import AppServiceError
from services.ingestion_job_store import IngestionJob, SQLiteIngestionJobStore

logger = logging.getLogger(__name__)


class DocumentIngestionWorker:
    def __init__(
        self,
        ingestion_service: DocumentIngestionService,
        job_store: SQLiteIngestionJobStore,
    ):
        self.ingestion_service = ingestion_service
        self.job_store = job_store

    def create_text_upload_job(self, filename: str) -> IngestionJob:
        return self.job_store.create_job(filename)

    async def process_text_upload(
        self,
        filename: str,
        text: str,
    ) -> IngestionJob:
        job = self.create_text_upload_job(filename)

        return await self.process_existing_text_upload_job(
            job_id=job.job_id,
            filename=filename,
            text=text,
        )

    async def process_existing_text_upload_job(
        self,
        job_id: str,
        filename: str,
        text: str,
    ) -> IngestionJob:
        processing_job = self.job_store.mark_processing(job_id)

        if processing_job is None:
            raise AppServiceError("Ingestion job could not be marked as processing.")

        try:
            ingestion_result = await self.ingestion_service.ingest_text(
                filename=filename,
                text=text,
            )
        except AppServiceError as ex:
            self.job_store.mark_failed(
                job_id=job_id,
                error_message=str(ex),
            )
            raise
        except Exception as ex:
            logger.exception(
                "Unexpected document ingestion failure job_id=%s filename=%s",
                job_id,
                filename,
            )

            self.job_store.mark_failed(
                job_id=job_id,
                error_message="Unexpected document ingestion failure.",
            )

            raise AppServiceError("Unexpected document ingestion failure.") from ex

        completed_job = self.job_store.mark_completed(
            job_id=job_id,
            document_id=ingestion_result.document_id,
            chunk_count=ingestion_result.chunk_count,
        )

        if completed_job is None:
            raise AppServiceError("Ingestion job could not be completed.")

        return completed_job

    async def process_existing_text_upload_job_safely(
        self,
        job_id: str,
        filename: str,
        text: str,
    ) -> None:
        try:
            await self.process_existing_text_upload_job(
                job_id=job_id,
                filename=filename,
                text=text,
            )
        except AppServiceError:
            logger.warning(
                "Document ingestion job failed job_id=%s filename=%s",
                job_id,
                filename,
            )

    def create_document_reindex_job(self, document_id: str) -> IngestionJob:
        stored_document = self.ingestion_service.store.get_document(document_id)

        if stored_document is None:
            raise AppServiceError("Document not found.")

        return self.job_store.create_job(stored_document.filename)

    async def process_existing_document_reindex_job(
            self,
            job_id: str,
            document_id: str,
    ) -> IngestionJob:
        processing_job = self.job_store.mark_processing(job_id)

        if processing_job is None:
            raise AppServiceError("Ingestion job could not be marked as processing.")

        try:
            stored_document = await self.ingestion_service.reindex_document(document_id)

            if stored_document is None:
                raise AppServiceError("Document not found.")

        except AppServiceError as ex:
            self.job_store.mark_failed(
                job_id=job_id,
                error_message=str(ex),
            )
            raise
        except Exception as ex:
            logger.exception(
                "Unexpected document re-index failure job_id=%s document_id=%s",
                job_id,
                document_id,
            )

            self.job_store.mark_failed(
                job_id=job_id,
                error_message="Unexpected document re-index failure.",
            )

            raise AppServiceError("Unexpected document re-index failure.") from ex

        completed_job = self.job_store.mark_completed(
            job_id=job_id,
            document_id=stored_document.document_id,
            chunk_count=len(stored_document.chunks),
        )

        if completed_job is None:
            raise AppServiceError("Ingestion job could not be completed.")

        return completed_job

    async def process_existing_document_reindex_job_safely(
            self,
            job_id: str,
            document_id: str,
    ) -> None:
        try:
            await self.process_existing_document_reindex_job(
                job_id=job_id,
                document_id=document_id,
            )
        except AppServiceError:
            logger.warning(
                "Document re-index job failed job_id=%s document_id=%s",
                job_id,
                document_id,
            )