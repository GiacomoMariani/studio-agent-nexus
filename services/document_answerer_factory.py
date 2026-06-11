from providers.document_qa_model_client_factory import (
    get_document_qa_model_client,
)
from services.document_answerer import (
    DocumentAnswerer,
    FallbackDocumentAnswerer,
    RuleBasedDocumentAnswerer,
)
from services.llm_document_answerer import LLMDocumentAnswerer
from services.rule_based_answerer import RuleBasedAnswerer
from settings import Settings


def get_document_answerer(settings: Settings) -> DocumentAnswerer:
    rule_answerer = RuleBasedDocumentAnswerer(
        answerer=RuleBasedAnswerer(),
    )

    if settings.document_answerer_type == "rule":
        return rule_answerer

    if settings.document_answerer_type == "llm":
        try:
            llm_answerer = LLMDocumentAnswerer(
                model_client=get_document_qa_model_client(settings),
            )
        except ValueError:
            if settings.document_qa_fallback_to_rule:
                return rule_answerer

            raise

        if settings.document_qa_fallback_to_rule:
            return FallbackDocumentAnswerer(
                primary_answerer=llm_answerer,
                fallback_answerer=rule_answerer,
            )

        return llm_answerer

    raise ValueError(
        "Unsupported DOCUMENT_ANSWERER_TYPE. "
        "Supported values: rule, llm."
    )


def resolve_provider(settings: Settings, answerer: DocumentAnswerer) -> str:
    """The provider that actually answered.

    Returns the configured provider only when an LLM answerer was built; returns "local"
    when the answerer is rule-based — either because DOCUMENT_ANSWERER_TYPE=rule, or because
    the LLM was unavailable (e.g. missing key) and we fell back to the rule path.
    """
    if (
        settings.document_answerer_type == "llm"
        and not isinstance(answerer, RuleBasedDocumentAnswerer)
    ):
        return settings.document_qa_model_client_type

    return "local"