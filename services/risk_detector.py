"""Risk & contradiction detection — finding model, detector abstraction, fallback wrapper.

A detector reads the ingested documents and returns `DetectedFinding`s (risks and
cross-document contradictions) in the exact shape the `/risks` store already expects
(`models/risk.py` / `services/risk_store.py`). This mirrors the document-answerer pattern:
a rule-based detector, an LLM detector, and a fallback wrapper, selected by
`services/risk_detector_factory.py`. No new persistence — findings are upserted through the
existing `SQLiteRiskStore` by `RiskDetectionService`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable

from services.exceptions import AppServiceError


@dataclass(frozen=True)
class DetectedFinding:
    """One detected finding, shaped like `RiskCreate`.

    `risk` findings use `description`/`source`; `contradiction` findings use the two-panel
    fields (`a_file`/`a_text` vs `b_file`/`b_text`). `risk_id` is deterministic and carries
    the reserved `auto-` origin prefix so a scan can refresh its own findings without
    touching hand-posted ones.
    """

    risk_id: str
    kind: str  # "risk" | "contradiction"
    severity: str  # Critical | High | Medium | Low
    title: str
    description: str = ""
    source: str = ""
    a_file: str = ""
    a_text: str = ""
    b_file: str = ""
    b_text: str = ""


@runtime_checkable
class SourceDocument(Protocol):
    """The slice of a stored document a detector reads. `StoredDocument` satisfies this."""

    filename: str
    original_text: str


class RiskDetector(Protocol):
    async def detect(self, documents: Sequence[SourceDocument]) -> list[DetectedFinding]: ...


class FallbackRiskDetector:
    """Run the primary detector; on `AppServiceError`, fall back to the secondary one.

    Mirrors `FallbackDocumentAnswerer`: keeps a misconfigured or failing LLM path from
    turning a scan into a 500 when fallback is enabled.
    """

    def __init__(self, *, primary: RiskDetector, fallback: RiskDetector) -> None:
        self._primary = primary
        self._fallback = fallback

    async def detect(self, documents: Sequence[SourceDocument]) -> list[DetectedFinding]:
        try:
            return await self._primary.detect(documents)
        except AppServiceError:
            return await self._fallback.detect(documents)
