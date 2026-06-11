"""LLMRiskDetector parses structured findings and fails safe on bad output (ticket-011)."""

import json
from types import SimpleNamespace

import pytest

from services.exceptions import AppServiceError
from services.llm_risk_detector import LLMRiskDetector


class StubModelClient:
    def __init__(self, *, response=None, error=None):
        self.response = response
        self.error = error
        self.prompts: list[str] = []

    async def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        return self.response


DOCS = [SimpleNamespace(filename="a.md", original_text="some text")]


@pytest.mark.asyncio
async def test_parses_valid_findings_and_normalizes_severity():
    payload = json.dumps([
        {"kind": "risk", "severity": "high", "title": "No purge window",
         "description": "PII piles up", "source": "a.md"},
        {"kind": "contradiction", "severity": "Critical", "title": "Tick rate",
         "a_file": "a.md", "a_text": "30 Hz", "b_file": "b.pdf", "b_text": "60 Hz"},
    ])
    findings = await LLMRiskDetector(StubModelClient(response=payload)).detect(DOCS)

    by_id = {f.risk_id: f for f in findings}
    assert set(by_id) == {"auto-risk-no-purge-window", "auto-contradiction-tick-rate"}
    assert by_id["auto-risk-no-purge-window"].severity == "High"  # normalized from "high"
    assert by_id["auto-contradiction-tick-rate"].b_text == "60 Hz"


@pytest.mark.asyncio
async def test_handles_code_fenced_json():
    payload = '```json\n[{"kind":"risk","severity":"Low","title":"X","description":"d","source":"a.md"}]\n```'
    findings = await LLMRiskDetector(StubModelClient(response=payload)).detect(DOCS)
    assert [f.risk_id for f in findings] == ["auto-risk-x"]


@pytest.mark.asyncio
async def test_skips_invalid_items_without_raising():
    payload = json.dumps([
        {"kind": "bogus", "severity": "High", "title": "X"},
        {"kind": "risk", "severity": "Nope", "title": "Y"},
        {"kind": "risk", "severity": "High", "title": ""},
    ])
    assert await LLMRiskDetector(StubModelClient(response=payload)).detect(DOCS) == []


@pytest.mark.asyncio
async def test_no_json_array_raises():
    with pytest.raises(AppServiceError):
        await LLMRiskDetector(StubModelClient(response="I found nothing.")).detect(DOCS)


@pytest.mark.asyncio
async def test_invalid_json_raises():
    with pytest.raises(AppServiceError):
        await LLMRiskDetector(StubModelClient(response="[not valid json]")).detect(DOCS)


@pytest.mark.asyncio
async def test_provider_error_raises_appservice():
    detector = LLMRiskDetector(StubModelClient(error=RuntimeError("boom")))
    with pytest.raises(AppServiceError):
        await detector.detect(DOCS)


@pytest.mark.asyncio
async def test_empty_documents_skip_the_model_call():
    client = StubModelClient(response="[]")
    assert await LLMRiskDetector(client).detect([]) == []
    assert client.prompts == []
