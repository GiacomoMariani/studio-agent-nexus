import pytest

from services.document_answerer_factory import get_document_answerer
from services.document_answering_service import DocumentAnsweringService
from services.document_store import InMemoryDocumentStore
from services.retrieval_service import ScoredChunk
from settings import Settings


class StubRetrievalService:
    def retrieve_with_scores(self, question, chunks, top_k):
        return [
            ScoredChunk(
                chunk=chunks[0],
                vector_score=1.0,
                keyword_score=1.0,
                hybrid_score=1.0,
            )
        ]


class StubUsageTrackingService:
    def __init__(self):
        self.records = []

    def record_usage(self, **kwargs):
        self.records.append(kwargs)

    def track_usage(self, **kwargs):
        self.records.append(kwargs)


@pytest.mark.asyncio
async def test_document_answering_service_uses_llm_document_answerer():
    store = InMemoryDocumentStore()

    stored_document = store.save_document(
        filename="policy.pdf",
        text="Refunds are available within 30 days.",
        chunk_payloads=[
            {
                "text": "Refunds are available within 30 days.",
                "embedding": [1.0, 0.0],
                "page_number": 4,
            }
        ],
    )

    usage_tracking_service = StubUsageTrackingService()

    service = DocumentAnsweringService(
        store=store,
        retrieval_service=StubRetrievalService(),
        answerer=get_document_answerer(
            Settings(
                document_answerer_type="llm",
                document_qa_model_client_type="fake",
            )
        ),
        usage_tracking_service=usage_tracking_service,
    )

    result = await service.answer(
        document_id=stored_document.document_id,
        question="What is the refund policy?",
        top_k=1,
    )

    assert result.answer == "Refunds are available within 30 days. [1]"
    assert result.was_fallback is False
    assert result.citations[0].filename == "policy.pdf"
    assert result.citations[0].page_number == 4
    assert usage_tracking_service.records[0]["model_name"] == "fake-document-qa+fallback-rule"