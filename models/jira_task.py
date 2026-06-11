"""Jira-task draft models — ephemeral, Jira-shaped task drafts (ticket-017).

A *draft* is an LLM- or rule-generated task proposed from one or more documents. Unlike
reviews / risks / planning-suggestions, drafts are **never persisted**: the generate route
returns them and the Board renders them in-session, each with a stubbed "Confirm on Jira".
Reuses the ``Department`` / ``Priority`` enums from the review models so a draft slots
straight into the existing board taxonomy; ``JiraIssueType`` is the only new enum.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from models.review import Department, Priority


class JiraIssueType(str, Enum):
    story = "Story"
    task = "Task"
    bug = "Bug"
    epic = "Epic"


class JiraTaskDraft(BaseModel):
    # use_enum_values: store/echo plain strings ("Story", "Backend"), not enum members.
    model_config = ConfigDict(use_enum_values=True)

    draft_id: str = Field(min_length=1)
    issue_type: JiraIssueType
    summary: str = Field(min_length=1)
    description: str = ""
    priority: Priority
    department: Department
    labels: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    story_points: int | None = None
    source: str = ""


class JiraTaskGenerateRequest(BaseModel):
    # None ⇒ generate from every document; otherwise the single selected document.
    document_id: str | None = None


def jira_task_schema() -> dict:
    """The draft schema for ``GET /admin/jira-tasks/schema`` — derived from the enums so it
    cannot drift from validation. Drafts are ephemeral: no identity, no upsert, no
    server-assigned fields, nothing stored."""
    return {
        "persistence": "none — drafts are generated on demand and never stored",
        "fields": {
            "draft_id": {"type": "string", "note": "deterministic per (source, summary)"},
            "issue_type": {"type": "string", "enum": [e.value for e in JiraIssueType]},
            "summary": {"type": "string", "required": True},
            "description": {"type": "string", "required": False, "default": ""},
            "priority": {"type": "string", "enum": [e.value for e in Priority]},
            "department": {"type": "string", "enum": [e.value for e in Department]},
            "labels": {"type": "array[string]", "required": False, "default": []},
            "acceptance_criteria": {"type": "array[string]", "required": False, "default": []},
            "story_points": {"type": "integer|null", "required": False, "default": None},
            "source": {"type": "string", "required": False, "note": "originating filename"},
        },
    }
