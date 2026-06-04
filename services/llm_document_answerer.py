from models.answering import AnswerResponse
from providers.model_client import ModelClient
from services.document_qa_prompt_builder import (
    RetrievedContextBlock,
    build_document_qa_prompt,
)

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
            return AnswerResponse(
                answer=FALLBACK_ANSWER,
                was_fallback=True,
            )

        was_fallback = _looks_like_fallback(answer)

        if not was_fallback and not _has_valid_source_citation(
                answer=answer,
                context_blocks=context_blocks,
        ):
            return AnswerResponse(
                answer=FALLBACK_ANSWER,
                was_fallback=True,
            )

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

def _has_valid_source_citation(
    answer: str,
    context_blocks: list[RetrievedContextBlock],
) -> bool:
    valid_source_markers = {
        f"[{block.source_id}]"
        for block in context_blocks
    }

    return any(
        marker in answer
        for marker in valid_source_markers
    )