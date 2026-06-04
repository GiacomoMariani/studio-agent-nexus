"""Planning suggestion models — "tasks you may still need", posted via the API.

Identity is the caller-supplied `suggestion_id`: POSTing the same id overwrites (upsert,
no PATCH). `updated_at` is server-set on each write. Suggestions only ever enter the DB
via POST — never seeded or hand-created. Reuses the `Department`/`Priority` enums from the
review models.
"""

from pydantic import BaseModel, ConfigDict, Field

from models.review import Department, Priority


class SuggestionCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    suggestion_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    reason: str = ""
    department: Department
    priority: Priority
    source: str = ""


class SuggestionResponse(BaseModel):
    suggestion_id: str
    title: str
    reason: str
    department: str
    priority: str
    source: str
    updated_at: str


def suggestion_post_schema() -> dict:
    """POST contract for `GET /planning-suggestions/schema`. Upsert keyed on
    `suggestion_id`; `updated_at` server-assigned on every write."""
    departments = [e.value for e in Department]
    priorities = [e.value for e in Priority]
    return {
        "identity": "suggestion_id",
        "write_semantics": "upsert — POST with an existing suggestion_id overwrites the record",
        "fields": {
            "suggestion_id": {"type": "string", "required": True, "identity": True},
            "title": {"type": "string", "required": True},
            "reason": {"type": "string", "required": False, "default": ""},
            "department": {"type": "string", "required": True, "enum": departments},
            "priority": {"type": "string", "required": True, "enum": priorities},
            "source": {"type": "string", "required": False, "default": ""},
        },
        "server_assigned": ["updated_at"],
    }
