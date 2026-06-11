import pytest

from services.chatbot_factory import get_chatbot
from services.llm_chatbot import FallbackChatbot
from services.rule_based_chatbot import RuleBasedChatbot
from settings import Settings


def test_get_chatbot_returns_rule_chatbot():
    chatbot = get_chatbot(Settings(chatbot_type="rule"))

    assert isinstance(chatbot, RuleBasedChatbot)


def test_get_chatbot_returns_fallback_llm_chatbot_with_fake_client():
    chatbot = get_chatbot(
        Settings(
            chatbot_type="llm",
            document_qa_model_client_type="fake",
        )
    )

    assert isinstance(chatbot, FallbackChatbot)


def test_get_chatbot_falls_back_to_rule_when_provider_key_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    chatbot = get_chatbot(
        Settings(
            chatbot_type="llm",
            document_qa_model_client_type="gemini",
            document_qa_model_name="gemini-2.5-flash",
        )
    )

    assert isinstance(chatbot, RuleBasedChatbot)


def test_get_chatbot_rejects_unsupported_type():
    with pytest.raises(ValueError) as exc_info:
        get_chatbot(Settings(chatbot_type="unsupported"))

    message = str(exc_info.value)

    assert "Unsupported CHATBOT_TYPE" in message
    assert "rule" in message
    assert "llm" in message
