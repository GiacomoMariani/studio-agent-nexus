from typing import Protocol

from models.summarization import SummarizeResponse


class Summarizer(Protocol):
    async def summarize(self, text: str, max_sentences: int) -> SummarizeResponse:
        ...
