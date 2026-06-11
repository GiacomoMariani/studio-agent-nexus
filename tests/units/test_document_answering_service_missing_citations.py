import pytest

from models.answering import AnswerResponse
from services.document_answering_service import DocumentAnsweringService
from services.document_store import InMemoryDocumentStore
from services.retrieval_service import ScoredChunk
from services.usage_tracking_service import estimate_tokens


class EmptyRetrievalService:
    def retrieve_with_scores(self, question, chunks, top_k):
        return []


class FactualAnswerWithoutRetrievedSources:
    model_name = "unsafe-test-answerer"

    async def answer(self, question, context_blocks):
        return AnswerResponse(
            answer="Refunds are available within 30 days.",
            was_fallback=False,
        )


@pytest.mark.asyncio
async def test_document_answering_service_falls_back_when_answer_has_no_citations():
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

    service = DocumentAnsweringService(
        store=store,
        retrieval_service=EmptyRetrievalService(),
        answerer=FactualAnswerWithoutRetrievedSources(),
    )

    result = await service.answer(
        document_id=stored_document.document_id,
        question="What is the refund policy?",
        top_k=1,
    )

    assert result.answer == (
        "I could not find this information in the uploaded documents."
    )
    assert result.was_fallback is True
    assert result.citations == []


class SingleChunkRetrievalService:
    def retrieve_with_scores(self, question, chunks, top_k):
        return [
            ScoredChunk(
                chunk=chunks[0],
                vector_score=1.0,
                keyword_score=1.0,
                hybrid_score=1.0,
            )
        ]


class AlwaysFallbackAnswerer:
    model_name = "stub"

    async def answer(self, question, context_blocks):
        return AnswerResponse(
            answer="I could not find this information in the uploaded documents.",
            was_fallback=True,
        )


@pytest.mark.asyncio
async def test_input_tokens_count_full_context_even_on_fallback():
    store = InMemoryDocumentStore()
    long_context = "The backend uses PostgreSQL and Redis for its data stores. " * 6
    stored_document = store.save_document(
        filename="arch.md",
        text=long_context,
        chunk_payloads=[
            {"text": long_context, "embedding": [1.0, 0.0], "page_number": 1}
        ],
    )

    service = DocumentAnsweringService(
        store=store,
        retrieval_service=SingleChunkRetrievalService(),
        answerer=AlwaysFallbackAnswerer(),
    )

    question = "Which data stores does the backend use?"
    result = await service.answer(
        document_id=stored_document.document_id,
        question=question,
        top_k=1,
    )

    # Fallback strips the visible citations...
    assert result.was_fallback is True
    assert result.citations == []
    # ...but the token count still reflects the full retrieved context, not just the question.
    assert result.input_tokens > estimate_tokens(question)


@pytest.mark.asyncio
async def test_document_answering_service_answer_all_falls_back_when_answer_has_no_citations():
    store = InMemoryDocumentStore()

    store.save_document(
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

    service = DocumentAnsweringService(
        store=store,
        retrieval_service=EmptyRetrievalService(),
        answerer=FactualAnswerWithoutRetrievedSources(),
    )

    result = await service.answer_all(
        question="What is the refund policy?",
        top_k=1,
    )

    assert result.answer == (
        "I could not find this information in the uploaded documents."
    )
    assert result.was_fallback is True
    assert result.citations == []
