import pytest

from services.classifier_factory import get_classifier
from services.llm_classifier import FallbackClassifier
from services.rule_based_classifier import RuleBasedClassifier
from settings import Settings


def test_get_classifier_returns_rule_classifier():
    classifier = get_classifier(Settings(classifier_type="rule"))

    assert isinstance(classifier, RuleBasedClassifier)


def test_get_classifier_returns_fallback_llm_classifier_with_fake_client():
    classifier = get_classifier(
        Settings(
            classifier_type="llm",
            document_qa_model_client_type="fake",
        )
    )

    assert isinstance(classifier, FallbackClassifier)


def test_get_classifier_falls_back_to_rule_when_provider_key_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    classifier = get_classifier(
        Settings(
            classifier_type="llm",
            document_qa_model_client_type="gemini",
            document_qa_model_name="gemini-2.5-flash",
        )
    )

    assert isinstance(classifier, RuleBasedClassifier)


def test_get_classifier_rejects_unsupported_type():
    with pytest.raises(ValueError) as exc_info:
        get_classifier(Settings(classifier_type="unsupported"))

    message = str(exc_info.value)

    assert "Unsupported CLASSIFIER_TYPE" in message
    assert "rule" in message
    assert "llm" in message
