import logging

from models.classification import ClassifyResponse
from services.classifier import Classifier
from services.exceptions import AppServiceError

logger = logging.getLogger(__name__)


class ClassificationService:
    def __init__(self, classifier: Classifier):
        self.classifier = classifier

    async def classify(self, text: str) -> ClassifyResponse:
        normalized_text = text.strip()

        try:
            return await self.classifier.classify(normalized_text)
        except Exception as ex:
            logger.exception("Classification failed for input text.")
            raise AppServiceError("Failed to classify text.") from ex