"""Select the Jira-task generator: rule | llm, with fallback-to-rule (ticket-017).

Mirrors `services/risk_detector_factory.py`: always builds the rule generator; for the LLM
path, builds the model client (falling back to rule if it's unavailable and fallback is
enabled) and wraps it in `FallbackJiraTaskGenerator` for runtime errors.
"""

from providers.document_qa_model_client_factory import get_document_qa_model_client
from services.jira_task_generator import FallbackJiraTaskGenerator, JiraTaskGenerator
from services.llm_jira_task_generator import LLMJiraTaskGenerator
from services.rule_based_jira_task_generator import RuleBasedJiraTaskGenerator
from settings import Settings


def get_jira_task_generator(settings: Settings) -> JiraTaskGenerator:
    rule_generator = RuleBasedJiraTaskGenerator()

    if settings.jira_task_generator_type == "rule":
        return rule_generator

    if settings.jira_task_generator_type == "llm":
        try:
            llm_generator = LLMJiraTaskGenerator(
                model_client=get_document_qa_model_client(settings),
            )
        except ValueError:
            if settings.jira_task_generation_fallback_to_rule:
                return rule_generator
            raise

        if settings.jira_task_generation_fallback_to_rule:
            return FallbackJiraTaskGenerator(primary=llm_generator, fallback=rule_generator)

        return llm_generator

    raise ValueError(
        "Unsupported JIRA_TASK_GENERATOR_TYPE. Supported values: rule, llm."
    )
