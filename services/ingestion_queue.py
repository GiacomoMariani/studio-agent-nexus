from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from fastapi import BackgroundTasks

from models.ingestion_queue_model import (
    DocumentReindexIngestionPayload,
    StoredTextUploadIngestionPayload,
    TextUploadIngestionPayload,
)
from services.stored_text_ingestion_processor import (
    process_stored_text_upload_payload_safely,
)

if TYPE_CHECKING:
    from services.document_ingestion_worker import DocumentIngestionWorker
    from services.uploaded_text_store import UploadedTextStore


class DocumentIngestionQueue(Protocol):
    def enqueue_text_upload(
        self,
        worker: DocumentIngestionWorker,
        payload: TextUploadIngestionPayload,
    ) -> None:
        ...

    def enqueue_stored_text_upload(
        self,
        worker: DocumentIngestionWorker,
        text_store: UploadedTextStore,
        payload: StoredTextUploadIngestionPayload,
    ) -> None:
        ...

    def enqueue_document_reindex(
            self,
            worker: DocumentIngestionWorker,
            payload: DocumentReindexIngestionPayload,
    ) -> None:
        ...


class FastAPIBackgroundTasksIngestionQueue:
    def __init__(self, background_tasks: BackgroundTasks):
        self.background_tasks = background_tasks

    def enqueue_text_upload(
        self,
        worker: DocumentIngestionWorker,
        payload: TextUploadIngestionPayload,
    ) -> None:
        self.background_tasks.add_task(
            worker.process_existing_text_upload_job_safely,
            payload.job_id,
            payload.filename,
            payload.text,
        )

    def enqueue_stored_text_upload(
        self,
        worker: DocumentIngestionWorker,
        text_store: UploadedTextStore,
        payload: StoredTextUploadIngestionPayload,
    ) -> None:
        self.background_tasks.add_task(
            process_stored_text_upload_payload_safely,
            worker,
            text_store,
            payload,
        )

    def enqueue_document_reindex(
            self,
            worker: DocumentIngestionWorker,
            payload: DocumentReindexIngestionPayload,
    ) -> None:
        self.background_tasks.add_task(
            worker.process_existing_document_reindex_job_safely,
            payload.job_id,
            payload.document_id,
        )