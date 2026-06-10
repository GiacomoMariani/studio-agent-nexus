from providers.document_qa_model_client_factory import (
    get_document_qa_model_client,
)
from services.llm_summarizer import FallbackSummarizer, LlmSummarizer
from services.rule_based_summarizer import RuleBasedSummarizer
from services.summarizer import Summarizer
from settings import Settings


def get_summarizer(settings: Settings) -> Summarizer:
    rule_summarizer = RuleBasedSummarizer()

    if settings.summarizer_type == "rule":
        return rule_summarizer

    if settings.summarizer_type == "llm":
        try:
            llm_summarizer = LlmSummarizer(
                model_client=get_document_qa_model_client(settings),
            )
        except ValueError:
            # No provider key / misconfigured client → degrade to the rule path.
            return rule_summarizer

        return FallbackSummarizer(
            primary=llm_summarizer,
            fallback=rule_summarizer,
        )

    raise ValueError(
        "Unsupported SUMMARIZER_TYPE. Supported values: rule, llm."
    )
