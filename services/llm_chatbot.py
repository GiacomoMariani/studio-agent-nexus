from models.chat import ChatResponse
from providers.model_client import ModelClient
from services.llm_fallback import run_with_fallback
from services.rule_based_chatbot import RuleBasedChatbot

_SYSTEM_PROMPT = (
    "You are the Studio Agent Nexus assistant, helping with game-production project "
    "management (tasks, docs, planning, risks). Be concise and helpful. If a request is "
    "outside that scope or you are unsure, say so briefly rather than inventing an answer."
)


class LlmChatbot:
    def __init__(self, model_client: ModelClient):
        self.model_client = model_client

    async def reply(self, message: str) -> ChatResponse:
        prompt = self._build_prompt(message)
        raw_response = await self.model_client.complete(prompt)
        reply = raw_response.strip()

        if not reply:
            raise ValueError("LLM returned an empty reply.")

        return ChatResponse(reply=reply)

    def _build_prompt(self, message: str) -> str:
        return (
            f"{_SYSTEM_PROMPT}\n\n"
            f"User: {message.strip()}\n"
            "Assistant:"
        )


class FallbackChatbot:
    def __init__(
        self,
        primary: LlmChatbot,
        fallback: RuleBasedChatbot,
    ):
        self.primary = primary
        self.fallback = fallback

    async def reply(self, message: str) -> ChatResponse:
        return await run_with_fallback(
            lambda: self.primary.reply(message),
            lambda: self.fallback.reply(message),
            label="chatbot",
        )
