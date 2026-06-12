"""Board import models — bulk replace payload for POST /admin/board/import (ticket-019).

The local→deployed board push sends one request carrying full entity sets. Each key is
optional: a key that is present (even as an empty list) means "replace the whole set with
exactly these items"; an absent/null key means "leave that set untouched". Items reuse the
per-entity Create models, so the entire payload is validated before any erase happens —
one invalid item anywhere rejects the whole import with 422.

`imported` counts the rows present after the replace: duplicate ids inside one payload
collapse through the stores' upsert-by-id semantics.
"""

from pydantic import BaseModel

from models.planning_suggestion import SuggestionCreate
from models.review import ReviewCreate
from models.risk import RiskCreate


class BoardImportRequest(BaseModel):
    reviews: list[ReviewCreate] | None = None
    planning_suggestions: list[SuggestionCreate] | None = None
    risks: list[RiskCreate] | None = None


class BoardImportEntityResult(BaseModel):
    deleted: int
    imported: int


class BoardImportResponse(BaseModel):
    reviews: BoardImportEntityResult | None = None
    planning_suggestions: BoardImportEntityResult | None = None
    risks: BoardImportEntityResult | None = None
