"""LLM-backed Jira-task generator — propose Jira-shaped drafts from documents (ticket-017).

Mirrors `LLMRiskDetector`: an async `generate` over a `ModelClient`, prompting for a JSON
array of task objects and validating each into a `JiraTaskDraft`. Unknown enum values are
**repaired** to safe defaults and summary-less items are **dropped** — output is never
surfaced raw. Any provider error or malformed top-level output raises `AppServiceError`, so
`FallbackJiraTaskGenerator` can drop back to the rule-based generator.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Sequence

from pydantic import ValidationError

from models.jira_task import JiraIssueType, JiraTaskDraft
from models.review import Department, Priority
from providers.model_client import ModelClient
from services.exceptions import AppServiceError
from services.jira_task_generator import SourceDocument

logger = logging.getLogger(__name__)

_MAX_DOC_CHARS = 6000  # keep each document's slice of the prompt bounded
_MAX_DRAFTS = 8  # cap the number of drafts returned per run

_ISSUE_BY_LOWER = {e.value.lower(): e.value for e in JiraIssueType}
_PRIORITY_BY_LOWER = {e.value.lower(): e.value for e in Priority}
_DEPT_BY_LOWER = {e.value.lower(): e.value for e in Department}

_PROMPT_HEADER = (
    "You are an experienced delivery lead. Read the project documents below and propose "
    "concrete Jira tasks a team could pick up — gaps to close, work implied by the specs, "
    "and follow-ups.\n\n"
    "Return ONLY a JSON array (no prose, no code fence). Each element is an object:\n"
    '  "issue_type": "Story" | "Task" | "Bug" | "Epic"\n'
    '  "summary": a short imperative task title\n'
    '  "description": one or two sentences of context\n'
    '  "priority": "Critical" | "High" | "Medium" | "Low"\n'
    '  "department": "Backend" | "Infra" | "Data" | "QA" | "Production"\n'
    '  "labels": array of short strings (optional)\n'
    '  "acceptance_criteria": array of short strings (optional)\n'
    '  "story_points": integer 1-13 (optional)\n'
    '  "source": the filename the task came from\n'
    f"Return at most {_MAX_DRAFTS} tasks. Return [] if you find nothing.\n\n"
    "DOCUMENTS:\n"
)


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "task"


def _build_prompt(documents: Sequence[SourceDocument]) -> str:
    blocks = []
    for document in documents:
        text = document.original_text.strip()
        if len(text) > _MAX_DOC_CHARS:
            text = text[:_MAX_DOC_CHARS] + " …[truncated]"
        blocks.append(f"--- FILE: {document.filename} ---\n{text}")
    return _PROMPT_HEADER + "\n\n".join(blocks)


def _extract_json_array(raw: str) -> list:
    raw = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()

    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise AppServiceError("Jira-task generator LLM did not return a JSON array.")

    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as ex:
        raise AppServiceError(f"Jira-task generator LLM returned invalid JSON: {ex}") from ex

    if not isinstance(data, list):
        raise AppServiceError("Jira-task generator LLM JSON was not an array.")
    return data


def _norm(value: object, lookup: dict, default: str) -> str:
    return lookup.get(str(value).strip().lower(), default)


def _str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _to_draft(item: object) -> JiraTaskDraft | None:
    """Validate one model-emitted object into a draft; repair enums, drop the unusable."""
    if not isinstance(item, dict):
        return None

    summary = str(item.get("summary", "")).strip()
    if not summary:
        return None

    story_points = item.get("story_points")
    if not isinstance(story_points, int) or isinstance(story_points, bool):
        story_points = None

    source = str(item.get("source", "")).strip()

    try:
        return JiraTaskDraft(
            draft_id=f"draft-{_slug(source + '-' + summary)}",
            issue_type=_norm(item.get("issue_type"), _ISSUE_BY_LOWER, "Task"),
            summary=summary,
            description=str(item.get("description", "")).strip(),
            priority=_norm(item.get("priority"), _PRIORITY_BY_LOWER, "Medium"),
            department=_norm(item.get("department"), _DEPT_BY_LOWER, "Production"),
            labels=_str_list(item.get("labels")),
            acceptance_criteria=_str_list(item.get("acceptance_criteria")),
            story_points=story_points,
            source=source,
        )
    except ValidationError:
        return None


class LLMJiraTaskGenerator:
    def __init__(self, model_client: ModelClient) -> None:
        self.model_client = model_client

    async def generate(self, documents: Sequence[SourceDocument]) -> list[JiraTaskDraft]:
        if not documents:
            return []

        try:
            raw = await self.model_client.complete(_build_prompt(documents))
        except Exception as ex:  # provider/transport failure → fall back to rule
            raise AppServiceError(f"Jira-task generator LLM call failed: {ex}") from ex

        drafts: list[JiraTaskDraft] = []
        seen: set[str] = set()
        for item in _extract_json_array(raw):
            draft = _to_draft(item)
            if draft is not None and draft.draft_id not in seen:
                seen.add(draft.draft_id)
                drafts.append(draft)
            if len(drafts) >= _MAX_DRAFTS:
                break
        return drafts
