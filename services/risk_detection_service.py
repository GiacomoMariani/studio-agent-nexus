"""Risk detection orchestration: load documents → detect → refresh the auto findings.

Writes only through the existing `SQLiteRiskStore` contract — no new persistence. A scan
**refreshes** the auto-detected findings (every `risk_id` carries the reserved `auto-`
prefix): it deletes the previously auto-detected rows and re-inserts the fresh ones, while
**hand-posted findings** (any non-`auto-` id, e.g. `RISK-001` from `POST /risks`) are left
untouched. Deterministic ids keep a re-run from duplicating.
"""

from __future__ import annotations

from services.risk_detector import RiskDetector
from services.risk_store import SQLiteRiskStore
from services.sqlite_document_store import SQLiteDocumentStore

AUTO_PREFIX = "auto-"


class RiskDetectionService:
    def __init__(
        self,
        *,
        document_store: SQLiteDocumentStore,
        risk_store: SQLiteRiskStore,
        detector: RiskDetector,
    ) -> None:
        self._document_store = document_store
        self._risk_store = risk_store
        self._detector = detector

    async def detect_and_store(self) -> list[dict]:
        documents = self._load_distinct_documents()
        findings = await self._detector.detect(documents)

        # Refresh: drop the prior auto-detected findings, keep hand-posted ones.
        for existing in self._risk_store.list():
            risk_id = existing["risk_id"]
            if risk_id.startswith(AUTO_PREFIX):
                self._risk_store.delete(risk_id)

        stored: list[dict] = []
        for finding in findings:
            record = self._risk_store.upsert(
                risk_id=finding.risk_id,
                kind=finding.kind,
                severity=finding.severity,
                title=finding.title,
                description=finding.description,
                source=finding.source,
                a_file=finding.a_file,
                a_text=finding.a_text,
                b_file=finding.b_file,
                b_text=finding.b_text,
            )
            stored.append(record)
        return stored

    def _load_distinct_documents(self) -> list:
        """One `StoredDocument` per filename — collapses the duplicate demo rows so a
        contradiction isn't reported once per copy."""
        distinct: dict[str, object] = {}
        for summary in self._document_store.list_documents():
            if summary.filename in distinct:
                continue
            document = self._document_store.get_document(summary.document_id)
            if document is not None:
                distinct[summary.filename] = document
        return list(distinct.values())
