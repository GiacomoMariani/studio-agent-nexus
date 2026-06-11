from typing import Protocol

from models.chat import ChatResponse


class Chatbot(Protocol):
    async def reply(self, message: str) -> ChatResponse:
        ...
