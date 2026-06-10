import pytest

from services.llm_answerer import FallbackAnswerer, LlmAnswerer
from services.rule_based_answerer import RuleBasedAnswerer


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
async def test_llm_answerer_returns_grounded_answer():
    answerer = LlmAnswerer(StubModelClient("  The refund window is 30 days.  "))

    result = await answerer.answer(
        "How long is the refund window?",
        "Refunds are reviewed within 30 days.",
    )

    assert result.answer == "The refund window is 30 days."
    assert result.was_fallback is False


@pytest.mark.asyncio
async def test_llm_answerer_marks_fallback_when_not_in_context():
    answerer = LlmAnswerer(
        StubModelClient("I could not find the answer in the provided context.")
    )

    result = await answerer.answer("Who is the CEO?", "Refunds within 30 days.")

    assert result.was_fallback is True


@pytest.mark.asyncio
async def test_llm_answerer_raises_on_empty_output():
    answerer = LlmAnswerer(StubModelClient("   "))

    with pytest.raises(ValueError):
        await answerer.answer("question", "context")


@pytest.mark.asyncio
async def test_fallback_answerer_uses_llm_when_it_succeeds():
    answerer = FallbackAnswerer(
        primary=LlmAnswerer(StubModelClient("A grounded LLM answer.")),
        fallback=RuleBasedAnswerer(),
    )

    result = await answerer.answer("anything?", "some unrelated context")

    assert result.answer == "A grounded LLM answer."


@pytest.mark.asyncio
async def test_fallback_answerer_falls_back_to_rule_on_llm_failure():
    answerer = FallbackAnswerer(
        primary=LlmAnswerer(BoomModelClient()),
        fallback=RuleBasedAnswerer(),
    )

    result = await answerer.answer(
        "What colour is the sky?",
        "Grass is green. The sky is blue.",
    )

    assert "blue" in result.answer.lower()
