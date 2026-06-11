"""get_jira_task_generator selects rule | llm and falls back to rule (ticket-017)."""

import pytest

from services.jira_task_generator import FallbackJiraTaskGenerator
from services.jira_task_generator_factory import get_jira_task_generator
from services.llm_jira_task_generator import LLMJiraTaskGenerator
from services.rule_based_jira_task_generator import RuleBasedJiraTaskGenerator
from settings import Settings


def test_rule_type_returns_rule_generator():
    generator = get_jira_task_generator(Settings(jira_task_generator_type="rule"))
    assert isinstance(generator, RuleBasedJiraTaskGenerator)


def test_llm_type_with_available_client_wraps_in_fallback():
    generator = get_jira_task_generator(
        Settings(
            jira_task_generator_type="llm",
            document_qa_model_client_type="fake",
            jira_task_generation_fallback_to_rule=True,
        )
    )
    assert isinstance(generator, FallbackJiraTaskGenerator)


def test_llm_type_without_fallback_returns_bare_llm():
    generator = get_jira_task_generator(
        Settings(
            jira_task_generator_type="llm",
            document_qa_model_client_type="fake",
            jira_task_generation_fallback_to_rule=False,
        )
    )
    assert isinstance(generator, LLMJiraTaskGenerator)


def test_unavailable_client_falls_back_to_rule():
    generator = get_jira_task_generator(
        Settings(
            jira_task_generator_type="llm",
            document_qa_model_client_type="not-a-provider",
            jira_task_generation_fallback_to_rule=True,
        )
    )
    assert isinstance(generator, RuleBasedJiraTaskGenerator)


def test_unavailable_client_without_fallback_raises():
    with pytest.raises(ValueError):
        get_jira_task_generator(
            Settings(
                jira_task_generator_type="llm",
                document_qa_model_client_type="not-a-provider",
                jira_task_generation_fallback_to_rule=False,
            )
        )


def test_unsupported_generator_type_raises():
    with pytest.raises(ValueError):
        get_jira_task_generator(Settings(jira_task_generator_type="bogus"))
