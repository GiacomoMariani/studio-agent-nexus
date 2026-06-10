from typing import Protocol

from models.answering import AnswerResponse


class Answerer(Protocol):
    async def answer(self, question: str, context: str) -> AnswerResponse:
        ...
