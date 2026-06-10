from providers.fake_document_qa_model_client import FakeDocumentQAModelClient
from providers.gemini_document_qa_model_client import GeminiDocumentQAModelClient
from providers.groq_document_qa_model_client import GroqDocumentQAModelClient
from providers.model_client import ModelClient
from providers.openai_document_qa_model_client import OpenAIDocumentQAModelClient
from settings import Settings


def get_document_qa_model_client(settings: Settings) -> ModelClient:
    if settings.document_qa_model_client_type == "fake":
        return FakeDocumentQAModelClient()

    if settings.document_qa_model_client_type == "gemini":
        return GeminiDocumentQAModelClient(
            model_name=settings.document_qa_model_name,
        )

    if settings.document_qa_model_client_type == "groq":
        return GroqDocumentQAModelClient(
            model_name=settings.document_qa_model_name,
        )

    if settings.document_qa_model_client_type == "openai":
        return OpenAIDocumentQAModelClient(
            model_name=settings.document_qa_model_name,
        )

    raise ValueError(
        "Unsupported DOCUMENT_QA_MODEL_CLIENT_TYPE. "
        "Supported values: fake, gemini, groq, openai."
    )
