"""RuleBasedJiraTaskGenerator turns document cues into deterministic Jira drafts (ticket-017)."""

from types import SimpleNamespace

import pytest

from services.rule_based_jira_task_generator import RuleBasedJiraTaskGenerator


def _doc(filename: str, text: str) -> SimpleNamespace:
    return SimpleNamespace(filename=filename, original_text=text)


GAP_DOC = _doc(
    "data_pipeline_spec.pdf",
    "The purge window for PII fields is not specified. Daily metrics use the UTC calendar day.",
)
BLOCKER_DOC = _doc(
    "release_readiness_checklist.md",
    "The staging environment that mirrors production has not been provisioned.",
)
PLAIN_DOC = _doc("intro.md", "Welcome to the project. This document describes the team.")


@pytest.mark.asyncio
async def test_gap_sentence_becomes_a_story_with_real_description():
    drafts = await RuleBasedJiraTaskGenerator().generate([GAP_DOC])

    assert len(drafts) == 1
    gap = drafts[0]
    assert gap.issue_type == "Story"
    assert gap.priority == "High"
    assert gap.department == "Data"  # inferred from "pipeline"/"data" in the filename
    assert "not specified" in gap.description.lower()
    assert gap.source == "data_pipeline_spec.pdf"
    assert gap.story_points == 5


@pytest.mark.asyncio
async def test_blocker_sentence_becomes_a_high_task():
    drafts = await RuleBasedJiraTaskGenerator().generate([BLOCKER_DOC])

    assert [d.issue_type for d in drafts] == ["Task"]
    assert drafts[0].priority == "High"
    assert drafts[0].department == "QA"  # "readiness"/"checklist"


@pytest.mark.asyncio
async def test_document_without_cues_yields_one_review_task():
    drafts = await RuleBasedJiraTaskGenerator().generate([PLAIN_DOC])

    assert len(drafts) == 1
    assert drafts[0].issue_type == "Task"
    assert drafts[0].summary.startswith("Review")


@pytest.mark.asyncio
async def test_output_is_deterministic_and_capped():
    generator = RuleBasedJiraTaskGenerator()
    first = [d.draft_id for d in await generator.generate([GAP_DOC, BLOCKER_DOC])]
    second = [d.draft_id for d in await generator.generate([GAP_DOC, BLOCKER_DOC])]

    assert first == second
    assert len(first) <= 8


@pytest.mark.asyncio
async def test_duplicate_filenames_collapsed():
    drafts = await RuleBasedJiraTaskGenerator().generate([GAP_DOC, GAP_DOC])
    ids = [d.draft_id for d in drafts]

    assert ids == list(dict.fromkeys(ids))  # no duplicate drafts from duplicate doc rows
    assert len(ids) == 1


@pytest.mark.asyncio
async def test_no_documents_yields_no_drafts():
    assert await RuleBasedJiraTaskGenerator().generate([]) == []
