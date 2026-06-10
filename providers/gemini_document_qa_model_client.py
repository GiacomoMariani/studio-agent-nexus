import os

from google import genai

from providers.model_client import ModelClient


class GeminiDocumentQAModelClient(ModelClient):
    def __init__(self, model_name: str):
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is required when "
                "DOCUMENT_QA_MODEL_CLIENT_TYPE=gemini."
            )

        self.model_name = model_name
        self.client = genai.Client(api_key=api_key)

    async def complete(self, prompt: str) -> str:
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )

        return (response.text or "").strip()
