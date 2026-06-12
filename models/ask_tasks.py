"""Ask-page "related & suggested tasks" models (ticket-018).

When an LLM answers on the Ask page, the user can pull (1) **related** existing board tasks
and (2) **suggested** new Jira-shaped drafts. Both are **ephemeral** — returned by the
`/documents/ask/task-suggestions` route and rendered in-session, never persisted. `RelatedTask`
is a board review/planning-suggestion plus its similarity `score`; `suggested` reuses the
ticket-017 `JiraTaskDraft`.
"""

from pydantic import BaseModel, Field

from models.jira_task import JiraTaskDraft


class AskTaskSuggestionRequest(BaseModel):
    question: str = Field(min_length=1)
    answer: str = ""


class RelatedTask(BaseModel):
    kind: str  # "review" | "suggestion"
    task_id: str
    title: str
    department: str
    priority: str
    source: str = ""
    score: float  # cosine similarity to the question, 0–1


class AskTaskSuggestionResponse(BaseModel):
    related: list[RelatedTask]
    suggested: list[JiraTaskDraft]
