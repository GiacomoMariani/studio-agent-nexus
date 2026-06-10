import logging

from models.summarization import SummarizeResponse
from services.exceptions import AppServiceError
from services.summarizer import Summarizer

logger = logging.getLogger(__name__)


class SummarizationService:
    def __init__(self, summarizer: Summarizer):
        self.summarizer = summarizer

    async def summarize(self, text: str, max_sentences: int) -> SummarizeResponse:
        normalized_text = text.strip()

        try:
            return await self.summarizer.summarize(normalized_text, max_sentences)
        except Exception as ex:
            logger.exception("Summarization failed for input text.")
            raise AppServiceError("Failed to summarize text.") from ex