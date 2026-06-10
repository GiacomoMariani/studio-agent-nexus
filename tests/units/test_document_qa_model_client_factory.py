import pytest

from providers.document_qa_model_client_factory import (
    get_document_qa_model_client,
)
from providers.fake_document_qa_model_client import FakeDocumentQAModelClient
from providers.gemini_document_qa_model_client import GeminiDocumentQAModelClient
from providers.groq_document_qa_model_client import GroqDocumentQAModelClient
from providers.openai_document_qa_model_client import OpenAIDocumentQAModelClient
from settings import Settings


def test_get_document_qa_model_client_returns_fake_client():
    client = get_document_qa_model_client(
        Settings(document_qa_model_client_type="fake")
    )

    assert isinstance(client, FakeDocumentQAModelClient)


def test_get_document_qa_model_client_returns_openai_client(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    client = get_document_qa_model_client(
        Settings(
            document_qa_model_client_type="openai",
            document_qa_model_name="gpt-4.1-mini",
        )
    )

    assert isinstance(client, OpenAIDocumentQAModelClient)
    assert client.model_name == "gpt-4.1-mini"


def test_get_document_qa_model_client_returns_gemini_client(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    client = get_document_qa_model_client(
        Settings(
            document_qa_model_client_type="gemini",
            document_qa_model_name="gemini-2.5-flash",
        )
    )

    assert isinstance(client, GeminiDocumentQAModelClient)
    assert client.model_name == "gemini-2.5-flash"


def test_get_document_qa_model_client_rejects_gemini_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(ValueError) as exc_info:
        get_document_qa_model_client(
            Settings(
                document_qa_model_client_type="gemini",
                document_qa_model_name="gemini-2.5-flash",
            )
        )

    assert "GEMINI_API_KEY is required" in str(exc_info.value)


def test_get_document_qa_model_client_returns_groq_client(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    client = get_document_qa_model_client(
        Settings(
            document_qa_model_client_type="groq",
            document_qa_model_name="llama-3.1-8b-instant",
        )
    )

    assert isinstance(client, GroqDocumentQAModelClient)
    assert client.model_name == "llama-3.1-8b-instant"


def test_get_document_qa_model_client_rejects_groq_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(ValueError) as exc_info:
        get_document_qa_model_client(
            Settings(
                document_qa_model_client_type="groq",
                document_qa_model_name="llama-3.1-8b-instant",
            )
        )

    assert "GROQ_API_KEY is required" in str(exc_info.value)


def test_get_document_qa_model_client_rejects_openai_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError) as exc_info:
        get_document_qa_model_client(
            Settings(
                document_qa_model_client_type="openai",
                document_qa_model_name="gpt-4.1-mini",
            )
        )

    assert "OPENAI_API_KEY is required" in str(exc_info.value)


def test_get_document_qa_model_client_rejects_unsupported_client_type():
    with pytest.raises(ValueError) as exc_info:
        get_document_qa_model_client(
            Settings(document_qa_model_client_type="unsupported")
        )

    message = str(exc_info.value)

    assert "Unsupported DOCUMENT_QA_MODEL_CLIENT_TYPE" in message
    assert "fake" in message
    assert "gemini" in message
    assert "groq" in message
    assert "openai" in message