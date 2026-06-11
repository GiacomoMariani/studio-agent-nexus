"""LLM-backed risk & contradiction detector — open-ended cross-document analysis.

Mirrors `LLMDocumentAnswerer`: an async `detect` over a `ModelClient`, prompting for a
structured JSON array of findings and validating it into `DetectedFinding`s. Any provider
error or malformed output raises `AppServiceError`, so `FallbackRiskDetector` can drop back
to the rule-based detector instead of 500-ing a scan.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Sequence

from providers.model_client import ModelClient
from services.exceptions import AppServiceError
from services.risk_detector import DetectedFinding, SourceDocument

logger = logging.getLogger(__name__)

_VALID_KINDS = {"risk", "contradiction"}
_VALID_SEVERITIES = {"Critical", "High", "Medium", "Low"}
_MAX_DOC_CHARS = 6000  # keep each document's slice of the prompt bounded

_PROMPT_HEADER = (
    "You are a meticulous technical reviewer. Analyse the project documents below and find:\n"
    "  (1) RISKS — an unresolved gap, missing decision, or blocker stated in ONE document.\n"
    "  (2) CONTRADICTIONS — claims in TWO different documents that conflict.\n\n"
    "Return ONLY a JSON array (no prose, no code fence). Each element is an object:\n"
    '  "kind": "risk" or "contradiction"\n'
    '  "severity": "Critical" | "High" | "Medium" | "Low"\n'
    '  "title": a short title\n'
    'For a risk also: "description" (one sentence) and "source" (the filename).\n'
    'For a contradiction also: "a_file","a_text" (one side) and "b_file","b_text" (the other).\n'
    "Return [] if you find nothing.\n\n"
    "DOCUMENTS:\n"
)


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "finding"


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
        raise AppServiceError("Risk detector LLM did not return a JSON array.")

    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as ex:
        raise AppServiceError(f"Risk detector LLM returned invalid JSON: {ex}") from ex

    if not isinstance(data, list):
        raise AppServiceError("Risk detector LLM JSON was not an array.")
    return data


def _to_finding(item: dict) -> DetectedFinding | None:
    """Validate one model-emitted object into a finding; None if it's unusable."""
    kind = str(item.get("kind", "")).strip().lower()
    severity = str(item.get("severity", "")).strip().capitalize()
    title = str(item.get("title", "")).strip()

    if kind not in _VALID_KINDS or severity not in _VALID_SEVERITIES or not title:
        return None

    risk_id = f"auto-{kind}-{_slug(title)}"

    if kind == "contradiction":
        return DetectedFinding(
            risk_id=risk_id,
            kind=kind,
            severity=severity,
            title=title,
            a_file=str(item.get("a_file", "")),
            a_text=str(item.get("a_text", "")),
            b_file=str(item.get("b_file", "")),
            b_text=str(item.get("b_text", "")),
        )

    return DetectedFinding(
        risk_id=risk_id,
        kind=kind,
        severity=severity,
        title=title,
        description=str(item.get("description", "")),
        source=str(item.get("source", "")),
    )


class LLMRiskDetector:
    def __init__(self, model_client: ModelClient) -> None:
        self.model_client = model_client

    async def detect(self, documents: Sequence[SourceDocument]) -> list[DetectedFinding]:
        if not documents:
            return []

        try:
            raw = await self.model_client.complete(_build_prompt(documents))
        except Exception as ex:  # provider/transport failure → fall back to rule
            raise AppServiceError(f"Risk detector LLM call failed: {ex}") from ex

        findings: list[DetectedFinding] = []
        seen: set[str] = set()
        for item in _extract_json_array(raw):
            if not isinstance(item, dict):
                continue
            finding = _to_finding(item)
            if finding is not None and finding.risk_id not in seen:
                seen.add(finding.risk_id)
                findings.append(finding)
        return findings
