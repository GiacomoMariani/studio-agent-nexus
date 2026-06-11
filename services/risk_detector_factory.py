"""Select the risk detector: rule | llm, with fallback-to-rule.

Mirrors `services/document_answerer_factory.py`: always builds the rule detector; for the
LLM path, builds the model client (falling back to rule if it's unavailable and fallback is
enabled) and wraps it in `FallbackRiskDetector` for runtime errors.
"""

from providers.document_qa_model_client_factory import get_document_qa_model_client
from services.llm_risk_detector import LLMRiskDetector
from services.risk_detector import FallbackRiskDetector, RiskDetector
from services.rule_based_risk_detector import RuleBasedRiskDetector
from settings import Settings


def get_risk_detector(settings: Settings) -> RiskDetector:
    rule_detector = RuleBasedRiskDetector()

    if settings.risk_detector_type == "rule":
        return rule_detector

    if settings.risk_detector_type == "llm":
        try:
            llm_detector = LLMRiskDetector(
                model_client=get_document_qa_model_client(settings),
            )
        except ValueError:
            if settings.risk_detection_fallback_to_rule:
                return rule_detector
            raise

        if settings.risk_detection_fallback_to_rule:
            return FallbackRiskDetector(primary=llm_detector, fallback=rule_detector)

        return llm_detector

    raise ValueError(
        "Unsupported RISK_DETECTOR_TYPE. Supported values: rule, llm."
    )
