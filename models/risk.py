"""Risk / contradiction models — findings posted via the risks API.

A finding is one entity with a ``kind``: a **risk** uses ``source``/``description``; a
**contradiction** uses the two-statement fields (``a_file``/``a_text``/``b_file``/
``b_text``). Identity is the caller-supplied ``risk_id``; POSTing the same id overwrites
(upsert). ``updated_at`` is server-set. Findings only ever enter the DB via POST.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Kind(str, Enum):
    risk = "risk"
    contradiction = "contradiction"


class Severity(str, Enum):
    critical = "Critical"
    high = "High"
    medium = "Medium"
    low = "Low"


class RiskCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    risk_id: str = Field(min_length=1)
    kind: Kind
    severity: Severity
    title: str = Field(min_length=1)
    description: str = ""
    source: str = ""
    # Contradiction-only: the two conflicting statements and their files.
    a_file: str = ""
    a_text: str = ""
    b_file: str = ""
    b_text: str = ""


class RiskResponse(BaseModel):
    risk_id: str
    kind: str
    severity: str
    title: str
    description: str
    source: str
    a_file: str
    a_text: str
    b_file: str
    b_text: str
    updated_at: str


def risk_post_schema() -> dict:
    """POST contract for `GET /risks/schema`. Upsert keyed on `risk_id`."""
    return {
        "identity": "risk_id",
        "write_semantics": "upsert — POST with an existing risk_id overwrites the record",
        "fields": {
            "risk_id": {"type": "string", "required": True, "identity": True},
            "kind": {"type": "string", "required": True, "enum": [e.value for e in Kind]},
            "severity": {"type": "string", "required": True, "enum": [e.value for e in Severity]},
            "title": {"type": "string", "required": True},
            "description": {"type": "string", "required": False, "note": "risk findings"},
            "source": {"type": "string", "required": False, "note": "risk findings"},
            "a_file": {"type": "string", "required": False, "note": "contradiction findings"},
            "a_text": {"type": "string", "required": False, "note": "contradiction findings"},
            "b_file": {"type": "string", "required": False, "note": "contradiction findings"},
            "b_text": {"type": "string", "required": False, "note": "contradiction findings"},
        },
        "server_assigned": ["updated_at"],
    }
