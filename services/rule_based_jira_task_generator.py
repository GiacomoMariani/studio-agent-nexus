"""Deterministic Jira-task generator — the offline / rule-based fallback (ticket-017).

Honest about being heuristic (like `RuleBasedRiskDetector`): it scans each document for
actionable cues — blockers, bugs, gaps, obligations — and turns the real sentence into a
Jira-shaped draft, inferring the department from the filename. A document with no cue yields
a single "review" task, so every selection produces at least one draft. Output is
deterministic (stable ordering, fixed mappings) so the default `pytest` run is free and
repeatable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from models.jira_task import JiraTaskDraft
from models.review import Department
from services.jira_task_generator import SourceDocument

_MAX_DRAFTS = 8
_STORY_POINTS = {"Critical": 8, "High": 5, "Medium": 3, "Low": 2}


@dataclass(frozen=True)
class _Cue:
    label: str
    issue_type: str
    priority: str
    verb: str
    needles: tuple[str, ...]  # any needle (case-insensitive) in a sentence triggers the cue


# Checked in order; the first matching cue wins for a given sentence.
_CUES: tuple[_Cue, ...] = (
    _Cue("blocker", "Task", "High", "Unblock",
         ("not been provisioned", "is blocked", "blocked by", "blocker", "cannot be")),
    _Cue("bug", "Bug", "High", "Fix",
         ("is broken", "regression", "fails to", "is incorrect", "defect")),
    _Cue("gap", "Story", "High", "Define",
         ("not specified", "not yet", "no hard", "no upper bound", "is missing",
          "undefined", "tbd", "not wired", "is not defined")),
    _Cue("follow-up", "Task", "Medium", "Implement",
         ("should ", "must ", "needs to", "is required", "we need")),
)

# Filename keyword → department. Checked in order; first hit wins, else Production.
_DEPT_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (Department.infra.value, ("fleet", "runbook", "infra", "deploy", "docker", "server", "ops")),
    (Department.data.value, ("pipeline", "data", "analytics", "metrics", "etl", "warehouse")),
    (Department.qa.value, ("readiness", "checklist", "release", "qa", "test", "quality")),
    (Department.backend.value, ("architecture", "backend", "api", "service", "schema")),
)


def _infer_department(filename: str) -> str:
    lowered = filename.lower()
    for dept, keywords in _DEPT_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return dept
    return Department.production.value


def _stem(filename: str) -> str:
    return re.sub(r"\.[a-z0-9]+$", "", filename, flags=re.IGNORECASE)


def _pretty_name(filename: str) -> str:
    return re.sub(r"[_\-]+", " ", _stem(filename)).strip().title() or filename


def _sentences(text: str) -> list[str]:
    """Split into sentences, dropping markdown tables and headings (like the risk detector)."""
    kept = []
    for line in text.replace("**", "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("|") or stripped.startswith("#"):
            continue
        kept.append(line)
    joined = re.sub(r"\s+", " ", " ".join(kept)).strip()
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", joined) if s.strip()]


def _shorten(text: str, limit: int = 90) -> str:
    text = text.strip().rstrip(".;")
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "task"


class RuleBasedJiraTaskGenerator:
    async def generate(self, documents: Sequence[SourceDocument]) -> list[JiraTaskDraft]:
        # Collapse duplicate document rows by filename (the demo set is seeded many times).
        by_name: dict[str, str] = {}
        for document in documents:
            by_name.setdefault(document.filename, document.original_text)

        drafts: list[JiraTaskDraft] = []
        seen: set[str] = set()

        for filename, text in by_name.items():
            department = _infer_department(filename)
            doc_drafts = self._cue_drafts(filename, text, department)
            if not doc_drafts:
                doc_drafts = [self._review_task(filename, department)]

            for draft in doc_drafts:
                if draft.draft_id in seen:
                    continue
                seen.add(draft.draft_id)
                drafts.append(draft)
                if len(drafts) >= _MAX_DRAFTS:
                    return drafts
        return drafts

    def _cue_drafts(self, filename: str, text: str, department: str) -> list[JiraTaskDraft]:
        drafts = []
        for sentence in _sentences(text):
            lowered = sentence.lower()
            for cue in _CUES:
                if any(needle in lowered for needle in cue.needles):
                    drafts.append(self._draft_from_cue(filename, department, cue, sentence))
                    break
        return drafts

    def _draft_from_cue(
        self, filename: str, department: str, cue: _Cue, sentence: str
    ) -> JiraTaskDraft:
        summary = f"{cue.verb}: {_shorten(sentence)}"
        return JiraTaskDraft(
            draft_id=f"draft-{_slug(filename + '-' + summary)}",
            issue_type=cue.issue_type,
            summary=summary,
            description=sentence.strip(),
            priority=cue.priority,
            department=department,
            labels=[cue.label, _stem(filename)],
            acceptance_criteria=[
                "Resolution captured in the source document",
                "Owner and target date assigned",
            ],
            story_points=_STORY_POINTS[cue.priority],
            source=filename,
        )

    def _review_task(self, filename: str, department: str) -> JiraTaskDraft:
        summary = f"Review {_pretty_name(filename)}"
        return JiraTaskDraft(
            draft_id=f"draft-{_slug(filename + '-' + summary)}",
            issue_type="Task",
            summary=summary,
            description=f"Review {filename} and capture any follow-up tasks.",
            priority="Medium",
            department=department,
            labels=["review", _stem(filename)],
            acceptance_criteria=["Document reviewed", "Follow-ups captured"],
            story_points=_STORY_POINTS["Medium"],
            source=filename,
        )
