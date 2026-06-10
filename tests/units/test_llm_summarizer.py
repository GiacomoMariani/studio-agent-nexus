import pytest

from services.llm_summarizer import FallbackSummarizer, LlmSummarizer
from services.rule_based_summarizer import RuleBasedSummarizer


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
async def test_llm_summarizer_returns_summary():
    summarizer = LlmSummarizer(StubModelClient("  A concise summary.  "))

    result = await summarizer.summarize("Long text here.", max_sentences=2)

    assert result.summary == "A concise summary."


@pytest.mark.asyncio
async def test_llm_summarizer_prompt_includes_sentence_budget():
    client = StubModelClient("Summary.")
    summarizer = LlmSummarizer(client)

    await summarizer.summarize("Long text.", max_sentences=3)

    assert "at most 3 sentences" in client.prompts[0]


@pytest.mark.asyncio
async def test_llm_summarizer_raises_on_empty_output():
    summarizer = LlmSummarizer(StubModelClient("   "))

    with pytest.raises(ValueError):
        await summarizer.summarize("Long text.", max_sentences=2)


@pytest.mark.asyncio
async def test_fallback_summarizer_uses_llm_when_it_succeeds():
    summarizer = FallbackSummarizer(
        primary=LlmSummarizer(StubModelClient("LLM summary.")),
        fallback=RuleBasedSummarizer(),
    )

    result = await summarizer.summarize(
        "First sentence. Second sentence.",
        max_sentences=1,
    )

    assert result.summary == "LLM summary."


@pytest.mark.asyncio
async def test_fallback_summarizer_falls_back_to_rule_on_llm_failure():
    summarizer = FallbackSummarizer(
        primary=LlmSummarizer(BoomModelClient()),
        fallback=RuleBasedSummarizer(),
    )

    result = await summarizer.summarize(
        "First sentence. Second sentence.",
        max_sentences=1,
    )

    assert result.summary == "First sentence."


@pytest.mark.asyncio
async def test_fallback_summarizer_falls_back_on_empty_llm_output():
    summarizer = FallbackSummarizer(
        primary=LlmSummarizer(StubModelClient("")),
        fallback=RuleBasedSummarizer(),
    )

    result = await summarizer.summarize(
        "First sentence. Second sentence.",
        max_sentences=1,
    )

    assert result.summary == "First sentence."
