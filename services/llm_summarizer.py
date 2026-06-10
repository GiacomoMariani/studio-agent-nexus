from models.summarization import SummarizeResponse
from providers.model_client import ModelClient
from services.llm_fallback import run_with_fallback
from services.rule_based_summarizer import RuleBasedSummarizer


class LlmSummarizer:
    def __init__(self, model_client: ModelClient):
        self.model_client = model_client

    async def summarize(self, text: str, max_sentences: int) -> SummarizeResponse:
        prompt = self._build_prompt(text, max_sentences)
        raw_response = await self.model_client.complete(prompt)
        summary = raw_response.strip()

        if not summary:
            raise ValueError("LLM returned an empty summary.")

        return SummarizeResponse(summary=summary)

    def _build_prompt(self, text: str, max_sentences: int) -> str:
        sentence_word = "sentence" if max_sentences == 1 else "sentences"

        return (
            f"Summarize the following text in at most {max_sentences} {sentence_word}. "
            "Write plain prose only — no preamble, labels, headings, or bullet points.\n\n"
            f"Text:\n{text.strip()}"
        )


class FallbackSummarizer:
    def __init__(
        self,
        primary: LlmSummarizer,
        fallback: RuleBasedSummarizer,
    ):
        self.primary = primary
        self.fallback = fallback

    async def summarize(self, text: str, max_sentences: int) -> SummarizeResponse:
        return await run_with_fallback(
            lambda: self.primary.summarize(text, max_sentences),
            lambda: self.fallback.summarize(text, max_sentences),
            label="summarizer",
        )
