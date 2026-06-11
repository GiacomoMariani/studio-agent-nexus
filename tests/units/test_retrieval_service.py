import math

import pytest

from providers.embedding_provider import LocalEmbeddingProvider
from services.document_ingestion_service import DocumentIngestionService
from services.document_store import InMemoryDocumentStore, StoredChunk
from services.retrieval_service import RetrievalService


class FakeEmbeddingProvider:
    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0]

    def embed_document(self, text: str) -> list[float]:
        return [1.0, 0.0]


def test_retrieval_returns_top_k_chunks():
    provider = LocalEmbeddingProvider()
    retrieval_service = RetrievalService(provider)

    chunks = [
        StoredChunk(
            chunk_id="chunk-1",
            text="FastAPI is the backend framework used in this project.",
            embedding=provider.embed_document(
                "FastAPI is the backend framework used in this project."
            ),
        ),
        StoredChunk(
            chunk_id="chunk-2",
            text="Pytest is used for testing.",
            embedding=provider.embed_document("Pytest is used for testing."),
        ),
        StoredChunk(
            chunk_id="chunk-3",
            text="Docker has not been added yet.",
            embedding=provider.embed_document("Docker has not been added yet."),
        ),
    ]

    results = retrieval_service.retrieve(
        question="What backend framework is used?",
        chunks=chunks,
        top_k=2,
    )

    assert len(results) == 2
    assert results[0].chunk_id == "chunk-1"


def test_retrieval_returns_empty_list_when_no_chunks_exist():
    retrieval_service = RetrievalService(FakeEmbeddingProvider())

    results = retrieval_service.retrieve(
        question="What backend framework is used?",
        chunks=[],
        top_k=2,
    )

    assert results == []


def test_retrieval_returns_empty_list_when_top_k_is_zero():
    retrieval_service = RetrievalService(FakeEmbeddingProvider())

    chunks = [
        StoredChunk(
            chunk_id="chunk-1",
            text="FastAPI is the backend framework.",
            embedding=[1.0, 0.0],
        )
    ]

    results = retrieval_service.retrieve(
        question="What backend framework is used?",
        chunks=chunks,
        top_k=0,
    )

    assert results == []


def test_hybrid_retrieval_uses_keyword_score_when_vector_scores_are_tied():
    retrieval_service = RetrievalService(
        embedding_provider=FakeEmbeddingProvider(),
        vector_weight=0.7,
        keyword_weight=0.3,
    )

    chunks = [
        StoredChunk(
            chunk_id="chunk-1",
            text="This section explains logging and monitoring.",
            embedding=[1.0, 0.0],
        ),
        StoredChunk(
            chunk_id="chunk-2",
            text="Docker is used to package and run the application.",
            embedding=[1.0, 0.0],
        ),
        StoredChunk(
            chunk_id="chunk-3",
            text="This section explains API request validation.",
            embedding=[1.0, 0.0],
        ),
    ]

    results = retrieval_service.retrieve(
        question="How is Docker used?",
        chunks=chunks,
        top_k=1,
    )

    assert len(results) == 1
    assert results[0].chunk_id == "chunk-2"


def test_retrieve_with_scores_returns_score_metadata():
    retrieval_service = RetrievalService(
        embedding_provider=FakeEmbeddingProvider(),
        vector_weight=0.7,
        keyword_weight=0.3,
    )

    chunks = [
        StoredChunk(
            chunk_id="chunk-1",
            text="FastAPI handles backend requests.",
            embedding=[1.0, 0.0],
        ),
        StoredChunk(
            chunk_id="chunk-2",
            text="Pytest handles automated tests.",
            embedding=[1.0, 0.0],
        ),
    ]

    scored_chunks = retrieval_service.retrieve_with_scores(
        question="What handles backend requests?",
        chunks=chunks,
        top_k=2,
    )

    assert len(scored_chunks) == 2
    assert scored_chunks[0].chunk.chunk_id == "chunk-1"
    assert scored_chunks[0].keyword_score > scored_chunks[1].keyword_score
    assert scored_chunks[0].hybrid_score > scored_chunks[1].hybrid_score


def test_retrieval_rejects_negative_weights():
    try:
        RetrievalService(
            embedding_provider=FakeEmbeddingProvider(),
            vector_weight=-1.0,
            keyword_weight=0.3,
        )
    except ValueError as exc:
        assert str(exc) == "vector_weight must be greater than or equal to 0."
    else:
        raise AssertionError("Expected ValueError.")


def test_retrieval_rejects_zero_total_weight():
    try:
        RetrievalService(
            embedding_provider=FakeEmbeddingProvider(),
            vector_weight=0.0,
            keyword_weight=0.0,
        )
    except ValueError as exc:
        assert str(exc) == "At least one retrieval weight must be greater than 0."
    else:
        raise AssertionError("Expected ValueError.")


@pytest.mark.asyncio
async def test_section_that_lists_outranks_passing_mention():
    # Regression for the "Which data stores…" retrieval miss: a dedicated section that
    # lists the answer must out-rank an intro that merely mentions the keywords.
    store = InMemoryDocumentStore()
    embedding_provider = LocalEmbeddingProvider()
    ingestion_service = DocumentIngestionService(
        store=store,
        embedding_provider=embedding_provider,
    )
    retrieval_service = RetrievalService(embedding_provider)

    text = (
        "# Backend Overview\n"
        "## 1. Purpose\n"
        "This document describes the servers and the data stores behind them.\n"
        "## 8. Data stores\n"
        "- Operational SQL for accounts and inventory.\n"
        "- Document store for player profiles.\n"
        "- Redis-style cache for sessions and queues.\n"
        "- Analytics warehouse for telemetry.\n"
    )

    result = await ingestion_service.ingest_text(filename="arch.md", text=text)
    document = store.get_document(result.document_id)

    scored_chunks = retrieval_service.retrieve_with_scores(
        question="Which data stores does the backend use?",
        chunks=document.chunks,
        top_k=1,
    )

    assert "Operational SQL" in scored_chunks[0].chunk.text


def test_relevance_floor_filters_by_raw_vector_score():
    # query embeds to [1,0]; chunk cosines are 1.0, 0.4, 0.0 — a 0.5 floor keeps only the first.
    service = RetrievalService(FakeEmbeddingProvider(), min_score=0.5)

    chunks = [
        StoredChunk(chunk_id="high", text="x", embedding=[1.0, 0.0]),
        StoredChunk(chunk_id="mid", text="y", embedding=[0.4, math.sqrt(1 - 0.16)]),
        StoredChunk(chunk_id="low", text="z", embedding=[0.0, 1.0]),
    ]

    scored = service.retrieve_with_scores("anything", chunks, top_k=5)

    assert [scored_chunk.chunk.chunk_id for scored_chunk in scored] == ["high"]


def test_relevance_floor_drops_off_topic_with_real_embeddings():
    provider = LocalEmbeddingProvider()
    service = RetrievalService(provider, min_score=0.3)

    chunks = [
        StoredChunk(
            chunk_id="c1",
            text="FastAPI is the backend framework used in this project.",
            embedding=provider.embed_document(
                "FastAPI is the backend framework used in this project."
            ),
        )
    ]

    # In-scope question clears the floor; an off-topic one falls below it → empty (fallback).
    assert len(service.retrieve("What backend framework is used?", chunks, top_k=3)) == 1
    assert service.retrieve("How do I bake sourdough bread?", chunks, top_k=3) == []


def test_no_floor_by_default_keeps_weak_matches():
    provider = LocalEmbeddingProvider()
    service = RetrievalService(provider)  # min_score defaults to 0.0 — floor off

    chunks = [
        StoredChunk(
            chunk_id="c1",
            text="FastAPI is the backend framework used in this project.",
            embedding=provider.embed_document(
                "FastAPI is the backend framework used in this project."
            ),
        )
    ]

    assert len(service.retrieve("How do I bake sourdough bread?", chunks, top_k=3)) == 1