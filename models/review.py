"""Review models — the persisted board item posted via the reviews API.

A "review" mirrors the board-task data the frontend shows. Its identity is the
caller-supplied `task_id`: POSTing the same `task_id` again **overwrites** the existing
record (upsert — there is no separate update/PATCH). `updated_at` is server-set on each
write. Reviews only ever enter the DB via POST — they are never seeded or hand-created.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Department(str, Enum):
    backend = "Backend"
    infra = "Infra"
    data = "Data"
    qa = "QA"
    production = "Production"


class Priority(str, Enum):
    critical = "Critical"
    high = "High"
    medium = "Medium"
    low = "Low"


class ReviewState(str, Enum):
    ai = "ai"
    lead = "lead"
    backlog = "backlog"
    todo = "todo"
    doing = "doing"
    done = "done"


class ReviewCreate(BaseModel):
    # use_enum_values: store/echo plain strings ("Backend"), not enum members.
    model_config = ConfigDict(use_enum_values=True)

    task_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    department: Department
    priority: Priority
    source: str = ""
    state: ReviewState


class ReviewResponse(BaseModel):
    task_id: str
    title: str
    description: str
    department: str
    priority: str
    source: str
    state: str
    updated_at: str


def review_post_schema() -> dict:
    """The POST contract for `GET /reviews/schema` — single source of truth for the
    allowed enum values, derived from the enums above so it cannot drift from validation.

    POST is an upsert keyed on `task_id`: re-posting the same `task_id` overwrites the
    existing record. `updated_at` is server-assigned on every write.
    """
    departments = [e.value for e in Department]
    priorities = [e.value for e in Priority]
    states = [e.value for e in ReviewState]
    return {
        "identity": "task_id",
        "write_semantics": "upsert — POST with an existing task_id overwrites the record",
        "fields": {
            "task_id": {"type": "string", "required": True, "identity": True},
            "title": {"type": "string", "required": True},
            "description": {"type": "string", "required": False, "default": ""},
            "department": {"type": "string", "required": True, "enum": departments},
            "priority": {"type": "string", "required": True, "enum": priorities},
            "source": {"type": "string", "required": False, "default": ""},
            "state": {"type": "string", "required": True, "enum": states},
        },
        "server_assigned": ["updated_at"],
    }
