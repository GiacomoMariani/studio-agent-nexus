import logging

from models.answering import AnswerResponse
from providers.model_client import ModelClient
from services.document_qa_prompt_builder import (
    RetrievedContextBlock,
    build_document_qa_prompt,
)

logger = logging.getLogger(__name__)

FALLBACK_ANSWER = (
    "I could not find this information in the uploaded documents."
)


class LLMDocumentAnswerer:
    def __init__(self, model_client: ModelClient):
        self.model_client = model_client
        self.model_name = getattr(
            model_client,
            "model_name",
            model_client.__class__.__name__,
        )

    async def answer(
        self,
        question: str,
        context_blocks: list[RetrievedContextBlock],
    ) -> AnswerResponse:
        if not context_blocks:
            return AnswerResponse(
                answer=FALLBACK_ANSWER,
                was_fallback=True,
            )

        prompt = build_document_qa_prompt(
            question=question,
            context_blocks=context_blocks,
        )

        raw_answer = await self.model_client.complete(prompt)
        answer = raw_answer.strip()

        if not answer:
            logger.warning("LLM returned an empty answer; using fallback.")
            return AnswerResponse(
                answer=FALLBACK_ANSWER,
                was_fallback=True,
            )

        # The retrieved sources are shown alongside the answer, so a missing inline [N]
        # marker no longer discards an otherwise-grounded answer (open models cite less
        # reliably than OpenAI). Only an explicit "not found" from the model is a fallback.
        was_fallback = _looks_like_fallback(answer)

        if was_fallback:
            logger.info("LLM declined to answer from the retrieved context.")

        return AnswerResponse(
            answer=answer,
            was_fallback=was_fallback,
        )


def _looks_like_fallback(answer: str) -> bool:
    lowered = answer.lower()

    fallback_markers = [
        "not found in the uploaded documents",
        "could not find this information",
        "could not find the answer",
        "does not contain",
        "not available in the provided context",
    ]

    return any(marker in lowered for marker in fallback_markers)
