import re

from models.classification import ClassifyResponse
from providers.model_client import ModelClient
from services.llm_fallback import run_with_fallback
from services.rule_based_classifier import RuleBasedClassifier

_VALID_CATEGORIES = ("billing", "technical", "refund", "general")


class LlmClassifier:
    def __init__(self, model_client: ModelClient):
        self.model_client = model_client

    async def classify(self, text: str) -> ClassifyResponse:
        prompt = self._build_prompt(text)
        raw_response = await self.model_client.complete(prompt)
        return ClassifyResponse(category=self._parse_category(raw_response))

    def _build_prompt(self, text: str) -> str:
        return (
            "Classify the support message into exactly one category.\n"
            "Categories:\n"
            "- billing: invoices, charges, payments, billing questions\n"
            "- technical: errors, bugs, crashes, login or product issues\n"
            "- refund: asking for a refund or money back\n"
            "- general: anything that does not fit the categories above\n"
            "Reply with only the single category word.\n\n"
            f"Message:\n{text.strip()}"
        )

    def _parse_category(self, raw_response: str) -> str:
        for token in re.findall(r"[a-z]+", raw_response.lower()):
            if token in _VALID_CATEGORIES:
                return token

        raise ValueError(
            f"LLM did not return a valid category: {raw_response!r}"
        )


class FallbackClassifier:
    def __init__(
        self,
        primary: LlmClassifier,
        fallback: RuleBasedClassifier,
    ):
        self.primary = primary
        self.fallback = fallback

    async def classify(self, text: str) -> ClassifyResponse:
        return await run_with_fallback(
            lambda: self.primary.classify(text),
            lambda: self.fallback.classify(text),
            label="classifier",
        )
