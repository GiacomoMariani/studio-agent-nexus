import pytest

from services.llm_fallback import run_with_fallback


@pytest.mark.asyncio
async def test_run_with_fallback_returns_primary_on_success():
    async def primary() -> str:
        return "primary"

    async def fallback() -> str:
        return "fallback"

    assert await run_with_fallback(primary, fallback) == "primary"


@pytest.mark.asyncio
async def test_run_with_fallback_returns_fallback_on_error():
    async def primary() -> str:
        raise RuntimeError("boom")

    async def fallback() -> str:
        return "fallback"

    assert await run_with_fallback(primary, fallback) == "fallback"
