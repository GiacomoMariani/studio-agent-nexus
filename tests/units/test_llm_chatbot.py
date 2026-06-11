import pytest

from services.llm_chatbot import FallbackChatbot, LlmChatbot
from services.rule_based_chatbot import RuleBasedChatbot


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
async def test_llm_chatbot_returns_reply():
    chatbot = LlmChatbot(StubModelClient("  Sure, I can help with that.  "))

    result = await chatbot.reply("How do I add a task?")

    assert result.reply == "Sure, I can help with that."


@pytest.mark.asyncio
async def test_llm_chatbot_prompt_includes_persona():
    client = StubModelClient("Hi.")
    chatbot = LlmChatbot(client)

    await chatbot.reply("hello")

    assert "Studio Agent Nexus assistant" in client.prompts[0]


@pytest.mark.asyncio
async def test_llm_chatbot_raises_on_empty_output():
    chatbot = LlmChatbot(StubModelClient("   "))

    with pytest.raises(ValueError):
        await chatbot.reply("hello")


@pytest.mark.asyncio
async def test_fallback_chatbot_uses_llm_when_it_succeeds():
    chatbot = FallbackChatbot(
        primary=LlmChatbot(StubModelClient("LLM reply.")),
        fallback=RuleBasedChatbot(),
    )

    result = await chatbot.reply("anything")

    assert result.reply == "LLM reply."


@pytest.mark.asyncio
async def test_fallback_chatbot_falls_back_to_rule_on_llm_failure():
    chatbot = FallbackChatbot(
        primary=LlmChatbot(BoomModelClient()),
        fallback=RuleBasedChatbot(),
    )

    result = await chatbot.reply("hello")

    assert result.reply == "Hello! How can I help?"
