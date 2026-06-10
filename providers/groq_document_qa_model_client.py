import os

from groq import AsyncGroq

from providers.model_client import ModelClient


class GroqDocumentQAModelClient(ModelClient):
    def __init__(self, model_name: str):
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is required when "
                "DOCUMENT_QA_MODEL_CLIENT_TYPE=groq."
            )

        self.model_name = model_name
        self.client = AsyncGroq(api_key=api_key)

    async def complete(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
        )

        return (response.choices[0].message.content or "").strip()
