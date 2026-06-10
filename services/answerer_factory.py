from providers.document_qa_model_client_factory import (
    get_document_qa_model_client,
)
from services.answerer import Answerer
from services.llm_answerer import FallbackAnswerer, LlmAnswerer
from services.rule_based_answerer import RuleBasedAnswerer
from settings import Settings


def get_answerer(settings: Settings) -> Answerer:
    rule_answerer = RuleBasedAnswerer()

    if settings.answerer_type == "rule":
        return rule_answerer

    if settings.answerer_type == "llm":
        try:
            llm_answerer = LlmAnswerer(
                model_client=get_document_qa_model_client(settings),
            )
        except ValueError:
            # No provider key / misconfigured client → degrade to the rule path.
            return rule_answerer

        return FallbackAnswerer(
            primary=llm_answerer,
            fallback=rule_answerer,
        )

    raise ValueError(
        "Unsupported ANSWERER_TYPE. Supported values: rule, llm."
    )
