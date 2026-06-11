import pytest

from services.document_qa_prompt_builder import RetrievedContextBlock
from services.llm_document_answerer import (
    FALLBACK_ANSWER,
    LLMDocumentAnswerer,
)


class StubModelClient:
    def __init__(self, response: str):
        self.response = response
        self.prompts: list[str] = []

    async def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


@pytest.mark.asyncio
async def test_llm_document_answerer_returns_model_answer_from_context():
    model_client = StubModelClient(
        response="Refunds are available within 30 days. [1]"
    )
    answerer = LLMDocumentAnswerer(model_client=model_client)

    result = await answerer.answer(
        question="What is the refund policy?",
        context_blocks=[
            RetrievedContextBlock(
                source_id=1,
                filename="policy.pdf",
                page_number=4,
                text="Refunds are available within 30 days.",
            )
        ],
    )

    assert result.answer == "Refunds are available within 30 days. [1]"
    assert result.was_fallback is False
    assert len(model_client.prompts) == 1
    assert "What is the refund policy?" in model_client.prompts[0]
    assert "[1] policy.pdf, page 4" in model_client.prompts[0]


@pytest.mark.asyncio
async def test_llm_document_answerer_includes_multiple_context_blocks_in_prompt():
    model_client = StubModelClient(
        response="FastAPI is used for the backend. [2]"
    )
    answerer = LLMDocumentAnswerer(model_client=model_client)

    result = await answerer.answer(
        question="What backend framework is used?",
        context_blocks=[
            RetrievedContextBlock(
                source_id=1,
                filename="frontend.txt",
                page_number=None,
                text="The frontend uses Streamlit.",
            ),
            RetrievedContextBlock(
                source_id=2,
                filename="backend.txt",
                page_number=None,
                text="FastAPI is used for the backend.",
            ),
        ],
    )

    assert result.answer == "FastAPI is used for the backend. [2]"
    assert result.was_fallback is False
    assert "[1] frontend.txt, page unavailable" in model_client.prompts[0]
    assert "[2] backend.txt, page unavailable" in model_client.prompts[0]


@pytest.mark.asyncio
async def test_llm_document_answerer_falls_back_without_context():
    model_client = StubModelClient(response="This should not be called.")
    answerer = LLMDocumentAnswerer(model_client=model_client)

    result = await answerer.answer(
        question="What is the refund policy?",
        context_blocks=[],
    )

    assert result.answer == FALLBACK_ANSWER
    assert result.was_fallback is True
    assert model_client.prompts == []


@pytest.mark.asyncio
async def test_llm_document_answerer_marks_model_fallback():
    model_client = StubModelClient(
        response="I could not find this information in the uploaded documents."
    )
    answerer = LLMDocumentAnswerer(model_client=model_client)

    result = await answerer.answer(
        question="Who handles billing?",
        context_blocks=[
            RetrievedContextBlock(
                source_id=1,
                filename="directory.txt",
                page_number=None,
                text="Support handles onboarding.",
            )
        ],
    )

    assert result.answer == (
        "I could not find this information in the uploaded documents."
    )
    assert result.was_fallback is True


@pytest.mark.asyncio
async def test_llm_document_answerer_allows_model_fallback_without_citation():
    model_client = StubModelClient(
        response="I could not find this information in the uploaded documents."
    )
    answerer = LLMDocumentAnswerer(model_client=model_client)

    result = await answerer.answer(
        question="What is the refund policy?",
        context_blocks=[
            RetrievedContextBlock(
                source_id=1,
                filename="policy.pdf",
                page_number=4,
                text="The onboarding process starts after contract signature.",
            )
        ],
    )

    assert result.answer == (
        "I could not find this information in the uploaded documents."
    )
    assert result.was_fallback is True


@pytest.mark.asyncio
async def test_llm_document_answerer_accepts_answer_without_inline_citation():
    # The retrieved sources are shown anyway, so a missing [N] marker must not discard a
    # grounded answer (open models cite less reliably than OpenAI).
    model_client = StubModelClient(
        response="Refunds are available within 30 days."
    )
    answerer = LLMDocumentAnswerer(model_client=model_client)

    result = await answerer.answer(
        question="What is the refund policy?",
        context_blocks=[
            RetrievedContextBlock(
                source_id=1,
                filename="policy.pdf",
                page_number=4,
                text="Refunds are available within 30 days.",
            )
        ],
    )

    assert result.answer == "Refunds are available within 30 days."
    assert result.was_fallback is False


@pytest.mark.asyncio
async def test_llm_document_answerer_falls_back_when_model_returns_blank_answer():
    model_client = StubModelClient(response="   ")
    answerer = LLMDocumentAnswerer(model_client=model_client)

    result = await answerer.answer(
        question="What is the refund policy?",
        context_blocks=[
            RetrievedContextBlock(
                source_id=1,
                filename="policy.pdf",
                page_number=4,
                text="Refunds are available within 30 days.",
            )
        ],
    )

    assert result.answer == FALLBACK_ANSWER
    assert result.was_fallback is True


def test_llm_document_answerer_uses_model_client_model_name():
    class NamedStubModelClient:
        model_name = "test-model-client"

        async def complete(self, prompt: str) -> str:
            return "Answer from context. [1]"

    answerer = LLMDocumentAnswerer(
        model_client=NamedStubModelClient(),
    )

    assert answerer.model_name == "test-model-client"


def test_llm_document_answerer_uses_client_class_name_when_model_name_missing():
    class UnnamedStubModelClient:
        async def complete(self, prompt: str) -> str:
            return "Answer from context. [1]"

    answerer = LLMDocumentAnswerer(
        model_client=UnnamedStubModelClient(),
    )

    assert answerer.model_name == "UnnamedStubModelClient"