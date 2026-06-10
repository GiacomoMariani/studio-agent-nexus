from providers.document_qa_model_client_factory import (
    get_document_qa_model_client,
)
from services.classifier import Classifier
from services.llm_classifier import FallbackClassifier, LlmClassifier
from services.rule_based_classifier import RuleBasedClassifier
from settings import Settings


def get_classifier(settings: Settings) -> Classifier:
    rule_classifier = RuleBasedClassifier()

    if settings.classifier_type == "rule":
        return rule_classifier

    if settings.classifier_type == "llm":
        try:
            llm_classifier = LlmClassifier(
                model_client=get_document_qa_model_client(settings),
            )
        except ValueError:
            # No provider key / misconfigured client → degrade to the rule path.
            return rule_classifier

        return FallbackClassifier(
            primary=llm_classifier,
            fallback=rule_classifier,
        )

    raise ValueError(
        "Unsupported CLASSIFIER_TYPE. Supported values: rule, llm."
    )
