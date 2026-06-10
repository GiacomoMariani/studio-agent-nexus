from types import SimpleNamespace

import pytest

from providers.groq_document_qa_model_client import (
    GroqDocumentQAModelClient,
)


class StubCompletions:
    def __init__(self):
        self.calls = []

    async def create(self, model: str, messages: list):
        self.calls.append(
            {
                "model": model,
                "messages": messages,
            }
        )

        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=" Grounded answer. [1] "),
                )
            ]
        )


class StubChat:
    def __init__(self):
        self.completions = StubCompletions()


class StubAsyncGroq:
    def __init__(self):
        self.chat = StubChat()


@pytest.mark.asyncio
async def test_groq_document_qa_model_client_completes_prompt(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    client = GroqDocumentQAModelClient(
        model_name="llama-3.1-8b-instant",
    )
    stub_client = StubAsyncGroq()
    client.client = stub_client

    result = await client.complete("Answer from this context only.")

    assert result == "Grounded answer. [1]"
    assert stub_client.chat.completions.calls == [
        {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "user", "content": "Answer from this context only."}
            ],
        }
    ]


def test_groq_document_qa_model_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(ValueError) as exc_info:
        GroqDocumentQAModelClient(model_name="llama-3.1-8b-instant")

    assert "GROQ_API_KEY is required" in str(exc_info.value)
