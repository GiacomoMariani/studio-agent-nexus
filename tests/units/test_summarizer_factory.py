import pytest

from services.llm_summarizer import FallbackSummarizer
from services.rule_based_summarizer import RuleBasedSummarizer
from services.summarizer_factory import get_summarizer
from settings import Settings


def test_get_summarizer_returns_rule_summarizer():
    summarizer = get_summarizer(Settings(summarizer_type="rule"))

    assert isinstance(summarizer, RuleBasedSummarizer)


def test_get_summarizer_returns_fallback_llm_summarizer_with_fake_client():
    summarizer = get_summarizer(
        Settings(
            summarizer_type="llm",
            document_qa_model_client_type="fake",
        )
    )

    assert isinstance(summarizer, FallbackSummarizer)


def test_get_summarizer_falls_back_to_rule_when_provider_key_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    summarizer = get_summarizer(
        Settings(
            summarizer_type="llm",
            document_qa_model_client_type="gemini",
            document_qa_model_name="gemini-2.5-flash",
        )
    )

    assert isinstance(summarizer, RuleBasedSummarizer)


def test_get_summarizer_rejects_unsupported_type():
    with pytest.raises(ValueError) as exc_info:
        get_summarizer(Settings(summarizer_type="unsupported"))

    message = str(exc_info.value)

    assert "Unsupported SUMMARIZER_TYPE" in message
    assert "rule" in message
    assert "llm" in message
