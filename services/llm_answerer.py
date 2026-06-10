from models.answering import AnswerResponse
from providers.model_client import ModelClient
from services.llm_fallback import run_with_fallback
from services.rule_based_answerer import RuleBasedAnswerer

_NOT_FOUND = "I could not find the answer in the provided context."


class LlmAnswerer:
    def __init__(self, model_client: ModelClient):
        self.model_client = model_client

    async def answer(self, question: str, context: str) -> AnswerResponse:
        prompt = self._build_prompt(question, context)
        raw_response = await self.model_client.complete(prompt)
        answer = raw_response.strip()

        if not answer:
            raise ValueError("LLM returned an empty answer.")

        return AnswerResponse(
            answer=answer,
            was_fallback=_NOT_FOUND.lower() in answer.lower(),
        )

    def _build_prompt(self, question: str, context: str) -> str:
        return (
            "Answer the question using only the provided context. "
            f'If the context does not contain the answer, reply exactly: "{_NOT_FOUND}"\n\n'
            f"Context:\n{context.strip()}\n\n"
            f"Question: {question.strip()}"
        )


class FallbackAnswerer:
    def __init__(
        self,
        primary: LlmAnswerer,
        fallback: RuleBasedAnswerer,
    ):
        self.primary = primary
        self.fallback = fallback

    async def answer(self, question: str, context: str) -> AnswerResponse:
        return await run_with_fallback(
            lambda: self.primary.answer(question, context),
            lambda: self.fallback.answer(question, context),
            label="answerer",
        )
