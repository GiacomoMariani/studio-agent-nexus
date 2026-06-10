from typing import Protocol

from models.classification import ClassifyResponse


class Classifier(Protocol):
    async def classify(self, text: str) -> ClassifyResponse:
        ...
