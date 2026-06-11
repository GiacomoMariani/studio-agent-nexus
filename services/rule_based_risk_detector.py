"""Deterministic risk & contradiction detector tuned to the demo knowledge base.

Honest about being demo-tuned (exactly like `RuleBasedAnswerer`): it looks for the specific
numeric-claim conflicts and gap statements planted across the seven Game-Title documents
(`demo/README.md`) and pulls the **real** evidence sentence out of each document. A finding
is emitted only when its evidence is actually present, so it degrades gracefully if a
document is missing or its wording changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from services.risk_detector import DetectedFinding, SourceDocument

ARCH = "backend_architecture_overview.md"
FLEET = "server_fleet_runbook.pdf"
PIPE = "data_pipeline_spec.pdf"
ANALYTICS = "player_analytics_and_metrics.pdf"
READINESS = "release_readiness_checklist.md"


@dataclass(frozen=True)
class _RiskSpec:
    key: str
    severity: str
    title: str
    file: str
    needles: tuple[str, ...]  # all must appear (case-insensitive) in one evidence sentence


@dataclass(frozen=True)
class _ContradictionSpec:
    key: str
    severity: str
    title: str
    a_file: str
    a_needles: tuple[str, ...]
    b_file: str
    b_needles: tuple[str, ...]


# Gap-pattern risks: a single document states an unresolved gap.
_RISKS: tuple[_RiskSpec, ...] = (
    _RiskSpec("fleet-ceiling", "Critical", "Autoscaling has no maximum fleet size",
              FLEET, ("hard upper bound",)),
    _RiskSpec("pii-retention", "High", "No PII purge window for player event data",
              PIPE, ("purge window", "not specified")),
    _RiskSpec("staging-blocker", "High", "Load testing blocked by unprovisioned staging",
              READINESS, ("staging environment", "provision")),
    _RiskSpec("ad-consent", "Medium", "Ad-consent flag not wired through the SDK",
              ANALYTICS, ("consent flag", "sdk")),
)

# Cross-document contradictions: two documents make conflicting numeric/definition claims.
_CONTRADICTIONS: tuple[_ContradictionSpec, ...] = (
    _ContradictionSpec("tick-rate", "Critical", "Server tick rate mismatch (30 Hz vs 60 Hz)",
                       ARCH, ("30 hz",), FLEET, ("60 hz",)),
    _ContradictionSpec("matchmaking-sla", "High", "Matchmaking SLA mismatch (p95 15 s vs 10 s)",
                       ARCH, ("matchmaking", "15 second"),
                       READINESS, ("matchmaking", "10 second")),
    _ContradictionSpec("retention-definition", "Medium",
                       "Retention definition mismatch (rolling 24 h vs UTC calendar day)",
                       PIPE, ("retention", "calendar day"),
                       ANALYTICS, ("retention", "rolling 24")),
)

_LEAD_NOISE = re.compile(r"^(open gap:|note:|for example,)\s*", re.IGNORECASE)
_PAGE_MARKER = re.compile(r"\[Page \d+\]")
_BULLET = re.compile(r"^[\-\*•>\s]+")


def _sentences(text: str) -> list[str]:
    """Split document text into sentences, dropping markdown tables and headings.

    Joins hard-wrapped lines back together before splitting, so an evidence sentence that
    wraps across lines stays whole; table rows (`| ... |`) and headings (`#`) are dropped
    so they never leak into a quoted finding.
    """
    kept_lines = []
    for line in _PAGE_MARKER.sub(" ", text).replace("**", "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("|") or stripped.startswith("#"):
            continue
        kept_lines.append(line)
    joined = re.sub(r"\s+", " ", " ".join(kept_lines)).strip()
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", joined) if s.strip()]


def _clean(sentence: str) -> str:
    sentence = _BULLET.sub("", sentence)
    sentence = _LEAD_NOISE.sub("", sentence)
    return sentence.strip()


def _evidence(text: str, needles: Sequence[str]) -> str:
    """The first sentence in `text` containing every needle (case-insensitive), cleaned."""
    wanted = [n.lower() for n in needles]
    for sentence in _sentences(text):
        lowered = sentence.lower()
        if all(needle in lowered for needle in wanted):
            return _clean(sentence)
    return ""


class RuleBasedRiskDetector:
    async def detect(self, documents: Sequence[SourceDocument]) -> list[DetectedFinding]:
        # Collapse duplicate document rows by filename (the demo set is seeded many times).
        by_name = {doc.filename: doc.original_text for doc in documents}
        findings: list[DetectedFinding] = []

        for spec in _CONTRADICTIONS:
            a_text = _evidence(by_name.get(spec.a_file, ""), spec.a_needles)
            b_text = _evidence(by_name.get(spec.b_file, ""), spec.b_needles)
            if a_text and b_text:
                findings.append(
                    DetectedFinding(
                        risk_id=f"auto-contradiction-{spec.key}",
                        kind="contradiction",
                        severity=spec.severity,
                        title=spec.title,
                        a_file=spec.a_file,
                        a_text=a_text,
                        b_file=spec.b_file,
                        b_text=b_text,
                    )
                )

        for spec in _RISKS:
            description = _evidence(by_name.get(spec.file, ""), spec.needles)
            if description:
                findings.append(
                    DetectedFinding(
                        risk_id=f"auto-risk-{spec.key}",
                        kind="risk",
                        severity=spec.severity,
                        title=spec.title,
                        description=description,
                        source=spec.file,
                    )
                )

        return findings
