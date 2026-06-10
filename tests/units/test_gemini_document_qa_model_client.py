from types import SimpleNamespace

import pytest

from providers.gemini_document_qa_model_client import (
    GeminiDocumentQAModelClient,
)


class StubModels:
    def __init__(self):
        self.calls = []

    async def generate_content(self, model: str, contents: str):
        self.calls.append(
            {
                "model": model,
                "contents": contents,
            }
        )

        return SimpleNamespace(text=" Grounded answer. [1] ")


class StubAio:
    def __init__(self):
        self.models = StubModels()


class StubGenAIClient:
    def __init__(self):
        self.aio = StubAio()


@pytest.mark.asyncio
async def test_gemini_document_qa_model_client_completes_prompt(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    client = GeminiDocumentQAModelClient(
        model_name="gemini-2.5-flash",
    )
    stub_client = StubGenAIClient()
    client.client = stub_client

    result = await client.complete("Answer from this context only.")

    assert result == "Grounded answer. [1]"
    assert stub_client.aio.models.calls == [
        {
            "model": "gemini-2.5-flash",
            "contents": "Answer from this context only.",
        }
    ]


def test_gemini_document_qa_model_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(ValueError) as exc_info:
        GeminiDocumentQAModelClient(model_name="gemini-2.5-flash")

    assert "GEMINI_API_KEY is required" in str(exc_info.value)
