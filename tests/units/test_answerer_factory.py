import pytest

from services.answerer_factory import get_answerer
from services.llm_answerer import FallbackAnswerer
from services.rule_based_answerer import RuleBasedAnswerer
from settings import Settings


def test_get_answerer_returns_rule_answerer():
    answerer = get_answerer(Settings(answerer_type="rule"))

    assert isinstance(answerer, RuleBasedAnswerer)


def test_get_answerer_returns_fallback_llm_answerer_with_fake_client():
    answerer = get_answerer(
        Settings(
            answerer_type="llm",
            document_qa_model_client_type="fake",
        )
    )

    assert isinstance(answerer, FallbackAnswerer)


def test_get_answerer_falls_back_to_rule_when_provider_key_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    answerer = get_answerer(
        Settings(
            answerer_type="llm",
            document_qa_model_client_type="gemini",
            document_qa_model_name="gemini-2.5-flash",
        )
    )

    assert isinstance(answerer, RuleBasedAnswerer)


def test_get_answerer_rejects_unsupported_type():
    with pytest.raises(ValueError) as exc_info:
        get_answerer(Settings(answerer_type="unsupported"))

    message = str(exc_info.value)

    assert "Unsupported ANSWERER_TYPE" in message
    assert "rule" in message
    assert "llm" in message
