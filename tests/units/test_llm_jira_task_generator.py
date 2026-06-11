"""LLMJiraTaskGenerator parses Jira drafts and fails safe on bad output (ticket-017)."""

import json
from types import SimpleNamespace

import pytest

from services.exceptions import AppServiceError
from services.llm_jira_task_generator import LLMJiraTaskGenerator


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
async def test_parses_valid_drafts_and_normalizes_enums():
    payload = json.dumps([
        {"issue_type": "story", "summary": "Define purge window", "description": "PII piles up",
         "priority": "high", "department": "data", "labels": ["gap"],
         "acceptance_criteria": ["documented"], "story_points": 5, "source": "a.md"},
        {"issue_type": "Task", "summary": "Wire consent flag", "priority": "Medium",
         "department": "Backend", "source": "a.md"},
    ])
    drafts = await LLMJiraTaskGenerator(StubModelClient(response=payload)).generate(DOCS)

    assert [d.summary for d in drafts] == ["Define purge window", "Wire consent flag"]
    first = drafts[0]
    assert first.issue_type == "Story"  # normalized from "story"
    assert first.priority == "High"
    assert first.department == "Data"
    assert first.labels == ["gap"]
    assert first.story_points == 5
    assert drafts[1].story_points is None


@pytest.mark.asyncio
async def test_handles_code_fenced_json():
    payload = (
        '```json\n[{"issue_type":"Bug","summary":"Fix crash","priority":"High",'
        '"department":"QA","source":"a.md"}]\n```'
    )
    drafts = await LLMJiraTaskGenerator(StubModelClient(response=payload)).generate(DOCS)
    assert [d.issue_type for d in drafts] == ["Bug"]


@pytest.mark.asyncio
async def test_repairs_unknown_enums_and_drops_summaryless():
    payload = json.dumps([
        {"issue_type": "Saga", "summary": "Weird type", "priority": "Whenever",
         "department": "Marketing", "source": "a.md"},
        {"summary": "", "issue_type": "Task", "priority": "Low", "department": "QA"},
    ])
    drafts = await LLMJiraTaskGenerator(StubModelClient(response=payload)).generate(DOCS)

    assert len(drafts) == 1  # the summary-less item is dropped
    repaired = drafts[0]
    assert repaired.issue_type == "Task"  # unknown → default
    assert repaired.priority == "Medium"
    assert repaired.department == "Production"


@pytest.mark.asyncio
async def test_caps_drafts_at_eight():
    payload = json.dumps([
        {"issue_type": "Task", "summary": f"Task {i}", "priority": "Low",
         "department": "QA", "source": "a.md"}
        for i in range(20)
    ])
    drafts = await LLMJiraTaskGenerator(StubModelClient(response=payload)).generate(DOCS)
    assert len(drafts) == 8


@pytest.mark.asyncio
async def test_no_json_array_raises():
    with pytest.raises(AppServiceError):
        await LLMJiraTaskGenerator(StubModelClient(response="I found nothing.")).generate(DOCS)


@pytest.mark.asyncio
async def test_invalid_json_raises():
    with pytest.raises(AppServiceError):
        await LLMJiraTaskGenerator(StubModelClient(response="[not valid json]")).generate(DOCS)


@pytest.mark.asyncio
async def test_provider_error_raises_appservice():
    generator = LLMJiraTaskGenerator(StubModelClient(error=RuntimeError("boom")))
    with pytest.raises(AppServiceError):
        await generator.generate(DOCS)


@pytest.mark.asyncio
async def test_empty_documents_skip_the_model_call():
    client = StubModelClient(response="[]")
    assert await LLMJiraTaskGenerator(client).generate([]) == []
    assert client.prompts == []
