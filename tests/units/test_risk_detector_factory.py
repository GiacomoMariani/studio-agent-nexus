"""get_risk_detector selects rule | llm and falls back to rule (ticket-011)."""

import pytest

from services.llm_risk_detector import LLMRiskDetector
from services.risk_detector import FallbackRiskDetector
from services.risk_detector_factory import get_risk_detector
from services.rule_based_risk_detector import RuleBasedRiskDetector
from settings import Settings


def test_rule_type_returns_rule_detector():
    detector = get_risk_detector(Settings(risk_detector_type="rule"))
    assert isinstance(detector, RuleBasedRiskDetector)


def test_llm_type_with_available_client_wraps_in_fallback():
    detector = get_risk_detector(
        Settings(
            risk_detector_type="llm",
            document_qa_model_client_type="fake",
            risk_detection_fallback_to_rule=True,
        )
    )
    assert isinstance(detector, FallbackRiskDetector)


def test_llm_type_without_fallback_returns_bare_llm():
    detector = get_risk_detector(
        Settings(
            risk_detector_type="llm",
            document_qa_model_client_type="fake",
            risk_detection_fallback_to_rule=False,
        )
    )
    assert isinstance(detector, LLMRiskDetector)


def test_unavailable_client_falls_back_to_rule():
    detector = get_risk_detector(
        Settings(
            risk_detector_type="llm",
            document_qa_model_client_type="not-a-provider",
            risk_detection_fallback_to_rule=True,
        )
    )
    assert isinstance(detector, RuleBasedRiskDetector)


def test_unavailable_client_without_fallback_raises():
    with pytest.raises(ValueError):
        get_risk_detector(
            Settings(
                risk_detector_type="llm",
                document_qa_model_client_type="not-a-provider",
                risk_detection_fallback_to_rule=False,
            )
        )


def test_unsupported_detector_type_raises():
    with pytest.raises(ValueError):
        get_risk_detector(Settings(risk_detector_type="bogus"))
