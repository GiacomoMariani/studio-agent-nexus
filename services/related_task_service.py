"""Related-task matching — find board tasks similar to a query, with local embeddings (ticket-018).

Reuses the same local sentence-transformer the retrieval service uses, so matching spends
**zero LLM tokens**. Embeddings are L2-normalized, so cosine similarity is a plain dot product
(mirrors `RetrievalService._dot_product`). Items are board reviews + planning-suggestions
collapsed to a common `{kind,task_id,title,text,department,priority,source}` shape by the caller.
"""

from __future__ import annotations

from typing import Protocol, Sequence

from models.ask_tasks import RelatedTask


class EmbeddingProvider(Protocol):
    def embed_query(self, text: str) -> list[float]: ...
    def embed_document(self, text: str) -> list[float]: ...


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    # Embeddings are L2-normalized → dot product is the cosine similarity.
    return sum(a * b for a, b in zip(left, right))


def _item_text(item: dict) -> str:
    return f"{item.get('title', '')}. {item.get('text', '')}".strip()


class RelatedTaskService:
    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        min_score: float = 0.3,
        top_n: int = 5,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._min_score = min_score
        self._top_n = top_n

    def match(self, query: str, items: Sequence[dict]) -> list[RelatedTask]:
        """The most similar board tasks to `query`, above the floor, best first (≤ top_n)."""
        query = query.strip()
        if not query or not items:
            return []

        query_embedding = self._embedding_provider.embed_query(query)

        scored: list[tuple[float, dict]] = []
        for item in items:
            item_embedding = self._embedding_provider.embed_document(_item_text(item))
            score = _cosine(query_embedding, item_embedding)
            if score >= self._min_score:
                scored.append((score, item))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [self._to_related(item, score) for score, item in scored[: self._top_n]]

    def max_similarity(self, text: str, others: Sequence[str]) -> float:
        """Highest cosine between `text` and any string in `others` (0.0 if none)."""
        others = [other for other in others if other]
        if not text or not others:
            return 0.0
        text_embedding = self._embedding_provider.embed_query(text)
        return max(
            _cosine(text_embedding, self._embedding_provider.embed_document(other))
            for other in others
        )

    @staticmethod
    def _to_related(item: dict, score: float) -> RelatedTask:
        return RelatedTask(
            kind=item.get("kind", ""),
            task_id=item.get("task_id", ""),
            title=item.get("title", ""),
            department=item.get("department", ""),
            priority=item.get("priority", ""),
            source=item.get("source", ""),
            score=round(float(score), 4),
        )
