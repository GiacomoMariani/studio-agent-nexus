import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def run_with_fallback(
    primary: Callable[[], Awaitable[T]],
    fallback: Callable[[], Awaitable[T]],
    *,
    label: str = "llm",
) -> T:
    """Run the primary (LLM) call; on any failure, return the rule-based fallback.

    Shared by the LLM-backed NLP services so an LLM error or invalid output never
    surfaces as a 500 — it degrades to the deterministic rule path instead.
    """
    try:
        return await primary()
    except Exception:
        logger.warning(
            "%s primary failed; using rule-based fallback.",
            label,
            exc_info=True,
        )
        return await fallback()
