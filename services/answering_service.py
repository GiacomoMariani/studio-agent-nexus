import logging

from models.answering import AnswerResponse
from services.answerer import Answerer
from services.exceptions import AppServiceError

logger = logging.getLogger(__name__)


class AnsweringService:
    def __init__(self, answerer: Answerer):
        self.answerer = answerer

    async def answer(self, question: str, context: str) -> AnswerResponse:
        normalized_question = question.strip()
        normalized_context = context.strip()

        try:
            return await self.answerer.answer(
                normalized_question,
                normalized_context,
            )
        except Exception as ex:
            logger.exception("Answering failed for input question and context.")
            raise AppServiceError("Failed to answer question.") from ex