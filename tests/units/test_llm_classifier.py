import pytest

from services.llm_classifier import FallbackClassifier, LlmClassifier
from services.rule_based_classifier import RuleBasedClassifier


class StubModelClient:
    def __init__(self, response: str):
        self.response = response
        self.prompts: list[str] = []

    async def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


class BoomModelClient:
    async def complete(self, prompt: str) -> str:
        raise RuntimeError("llm unavailable")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw_response, expected",
    [
        ("billing", "billing"),
        ("Category: refund.", "refund"),
        ("```\ntechnical\n```", "technical"),
        ("  General  ", "general"),
    ],
)
async def test_llm_classifier_parses_valid_category(raw_response, expected):
    classifier = LlmClassifier(StubModelClient(raw_response))

    result = await classifier.classify("my card was charged twice")

    assert result.category == expected


@pytest.mark.asyncio
async def test_llm_classifier_raises_on_invalid_category():
    classifier = LlmClassifier(StubModelClient("I am not sure about that"))

    with pytest.raises(ValueError):
        await classifier.classify("hello there")


@pytest.mark.asyncio
async def test_fallback_classifier_uses_llm_when_it_succeeds():
    classifier = FallbackClassifier(
        primary=LlmClassifier(StubModelClient("billing")),
        fallback=RuleBasedClassifier(),
    )

    # No keyword the rule classifier would catch — proves the LLM result is used.
    result = await classifier.classify("the statement looks off this month")

    assert result.category == "billing"


@pytest.mark.asyncio
async def test_fallback_classifier_falls_back_to_rule_on_llm_failure():
    classifier = FallbackClassifier(
        primary=LlmClassifier(BoomModelClient()),
        fallback=RuleBasedClassifier(),
    )

    result = await classifier.classify("I would like a refund please")

    assert result.category == "refund"
