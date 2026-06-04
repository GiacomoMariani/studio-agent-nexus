import re
from dataclasses import dataclass

from providers.embedding_provider import LocalEmbeddingProvider
from services.document_store import StoredChunk

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}


@dataclass(frozen=True)
class ScoredChunk:
    chunk: StoredChunk
    vector_score: float
    keyword_score: float
    hybrid_score: float


class RetrievalService:
    def __init__(
        self,
        embedding_provider: LocalEmbeddingProvider,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ):
        if vector_weight < 0:
            raise ValueError("vector_weight must be greater than or equal to 0.")

        if keyword_weight < 0:
            raise ValueError("keyword_weight must be greater than or equal to 0.")

        if vector_weight == 0 and keyword_weight == 0:
            raise ValueError("At least one retrieval weight must be greater than 0.")

        self.embedding_provider = embedding_provider
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    def retrieve(
        self,
        question: str,
        chunks: list[StoredChunk],
        top_k: int = 3,
    ) -> list[StoredChunk]:
        scored_chunks = self.retrieve_with_scores(
            question=question,
            chunks=chunks,
            top_k=top_k,
        )

        return [scored_chunk.chunk for scored_chunk in scored_chunks]

    def retrieve_with_scores(
        self,
        question: str,
        chunks: list[StoredChunk],
        top_k: int = 3,
    ) -> list[ScoredChunk]:
        if not chunks:
            return []

        if top_k <= 0:
            return []

        query_embedding = self.embedding_provider.embed_query(question)

        raw_scored_chunks: list[tuple[float, float, StoredChunk]] = []

        for chunk in chunks:
            vector_score = self._dot_product(query_embedding, chunk.embedding)
            keyword_score = self._keyword_overlap_score(question, chunk.text)

            raw_scored_chunks.append(
                (
                    vector_score,
                    keyword_score,
                    chunk,
                )
            )

        normalized_vector_scores = self._normalize_scores(
            [item[0] for item in raw_scored_chunks]
        )

        normalized_keyword_scores = self._normalize_scores(
            [item[1] for item in raw_scored_chunks]
        )

        scored_chunks: list[ScoredChunk] = []

        for index, (_, _, chunk) in enumerate(raw_scored_chunks):
            normalized_vector_score = normalized_vector_scores[index]
            normalized_keyword_score = normalized_keyword_scores[index]

            hybrid_score = (
                self.vector_weight * normalized_vector_score
                + self.keyword_weight * normalized_keyword_score
            )

            scored_chunks.append(
                ScoredChunk(
                    chunk=chunk,
                    vector_score=normalized_vector_score,
                    keyword_score=normalized_keyword_score,
                    hybrid_score=hybrid_score,
                )
            )

        scored_chunks.sort(
            key=lambda scored_chunk: (
                scored_chunk.hybrid_score,
                scored_chunk.keyword_score,
                scored_chunk.vector_score,
            ),
            reverse=True,
        )

        return scored_chunks[:top_k]

    def _keyword_overlap_score(
        self,
        question: str,
        text: str,
    ) -> float:
        question_terms = self._tokenize(question)
        text_terms = self._tokenize(text)

        if not question_terms or not text_terms:
            return 0.0

        matches = question_terms.intersection(text_terms)

        return len(matches) / len(question_terms)

    def _tokenize(self, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower())
            if len(token) > 2 and token not in STOPWORDS
        }

    def _normalize_scores(self, scores: list[float]) -> list[float]:
        if not scores:
            return []

        minimum_score = min(scores)
        maximum_score = max(scores)

        if minimum_score == maximum_score:
            return [0.0 for _ in scores]

        score_range = maximum_score - minimum_score

        return [
            (score - minimum_score) / score_range
            for score in scores
        ]

    def _dot_product(
        self,
        left: list[float],
        right: list[float],
    ) -> float:
        return sum(
            left_value * right_value
            for left_value, right_value in zip(left, right)
        )