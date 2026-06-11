import pytest

from services.document_answerer import (
    FallbackDocumentAnswerer,
    RuleBasedDocumentAnswerer,
)
from services.document_answerer_factory import get_document_answerer, resolve_provider
from services.llm_document_answerer import LLMDocumentAnswerer
from settings import Settings


def test_get_document_answerer_returns_rule_based_answerer_by_default():
    answerer = get_document_answerer(
        Settings(document_answerer_type="rule")
    )

    assert isinstance(answerer, RuleBasedDocumentAnswerer)


def test_get_document_answerer_returns_llm_answerer_with_rule_fallback_by_default():
    answerer = get_document_answerer(
        Settings(
            document_answerer_type="llm",
            document_qa_model_client_type="fake",
        )
    )

    assert isinstance(answerer, FallbackDocumentAnswerer)
    assert answerer.model_name == "fake-document-qa+fallback-rule"


def test_get_document_answerer_returns_llm_answerer_without_rule_fallback():
    answerer = get_document_answerer(
        Settings(
            document_answerer_type="llm",
            document_qa_model_client_type="fake",
            document_qa_fallback_to_rule=False,
        )
    )

    assert isinstance(answerer, LLMDocumentAnswerer)
    assert answerer.model_name == "fake-document-qa"


def test_get_document_answerer_falls_back_to_rule_when_openai_key_missing_and_fallback_enabled(
    monkeypatch,
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    answerer = get_document_answerer(
        Settings(
            document_answerer_type="llm",
            document_qa_model_client_type="openai",
            document_qa_model_name="gpt-4.1-mini",
            document_qa_fallback_to_rule=True,
        )
    )

    assert isinstance(answerer, RuleBasedDocumentAnswerer)


def test_get_document_answerer_falls_back_to_rule_when_gemini_key_missing_and_fallback_enabled(
    monkeypatch,
):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    answerer = get_document_answerer(
        Settings(
            document_answerer_type="llm",
            document_qa_model_client_type="gemini",
            document_qa_model_name="gemini-2.5-flash",
            document_qa_fallback_to_rule=True,
        )
    )

    assert isinstance(answerer, RuleBasedDocumentAnswerer)


def test_get_document_answerer_raises_when_openai_key_missing_and_fallback_disabled(
    monkeypatch,
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError) as exc_info:
        get_document_answerer(
            Settings(
                document_answerer_type="llm",
                document_qa_model_client_type="openai",
                document_qa_model_name="gpt-4.1-mini",
                document_qa_fallback_to_rule=False,
            )
        )

    assert "OPENAI_API_KEY is required" in str(exc_info.value)


def test_get_document_answerer_rejects_unsupported_answerer_type():
    with pytest.raises(ValueError) as exc_info:
        get_document_answerer(
            Settings(document_answerer_type="unsupported")
        )

    message = str(exc_info.value)

    assert "Unsupported DOCUMENT_ANSWERER_TYPE" in message
    assert "rule" in message
    assert "llm" in message

def test_get_document_answerer_returns_openai_llm_with_rule_fallback_when_key_exists(
    monkeypatch,
):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    answerer = get_document_answerer(
        Settings(
            document_answerer_type="llm",
            document_qa_model_client_type="openai",
            document_qa_model_name="gpt-4.1-mini",
            document_qa_fallback_to_rule=True,
        )
    )

    assert isinstance(answerer, FallbackDocumentAnswerer)
    assert answerer.model_name == "gpt-4.1-mini+fallback-rule"


def test_resolve_provider_reports_configured_when_llm_built():
    settings = Settings(
        document_answerer_type="llm",
        document_qa_model_client_type="fake",
    )
    answerer = get_document_answerer(settings)

    assert resolve_provider(settings, answerer) == "fake"


def test_resolve_provider_reports_local_when_llm_unavailable(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    settings = Settings(
        document_answerer_type="llm",
        document_qa_model_client_type="gemini",
        document_qa_model_name="gemini-2.5-flash",
        document_qa_fallback_to_rule=True,
    )
    answerer = get_document_answerer(settings)

    assert resolve_provider(settings, answerer) == "local"


def test_resolve_provider_reports_local_for_rule_type():
    settings = Settings(document_answerer_type="rule")
    answerer = get_document_answerer(settings)

    assert resolve_provider(settings, answerer) == "local"