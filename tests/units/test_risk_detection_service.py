"""RiskDetectionService refreshes auto findings, preserves manual ones, dedups docs."""

from types import SimpleNamespace

import pytest

from services.risk_detection_service import RiskDetectionService
from services.risk_detector import DetectedFinding
from services.risk_store import SQLiteRiskStore

FLEET = DetectedFinding(
    risk_id="auto-risk-fleet-ceiling", kind="risk", severity="Critical",
    title="Fleet ceiling", description="d", source="server_fleet_runbook.pdf",
)
TICK = DetectedFinding(
    risk_id="auto-contradiction-tick-rate", kind="contradiction", severity="Critical",
    title="Tick rate", a_file="a.md", a_text="30", b_file="b.pdf", b_text="60",
)


class StubDetector:
    def __init__(self, findings):
        self._findings = findings
        self.documents = None

    async def detect(self, documents):
        self.documents = list(documents)
        return self._findings


class StubDocStore:
    def __init__(self, summaries=(), docs=None):
        self._summaries = list(summaries)
        self._docs = docs or {}
        self.fetched = []

    def list_documents(self):
        return self._summaries

    def get_document(self, document_id):
        self.fetched.append(document_id)
        return self._docs.get(document_id)


@pytest.mark.asyncio
async def test_refreshes_auto_findings_and_preserves_manual(tmp_path):
    store = SQLiteRiskStore(str(tmp_path / "app.db"))
    store.upsert(risk_id="RISK-001", kind="risk", severity="High", title="Hand posted",
                 description="keep me", source="x.md")
    store.upsert(risk_id="auto-risk-stale", kind="risk", severity="Low", title="old",
                 description="drop me", source="y.md")

    service = RiskDetectionService(
        document_store=StubDocStore(), risk_store=store,
        detector=StubDetector([FLEET, TICK]),
    )
    stored = await service.detect_and_store()

    ids = {row["risk_id"] for row in store.list()}
    assert "RISK-001" in ids                  # hand-posted preserved
    assert "auto-risk-stale" not in ids       # prior auto refreshed away
    assert {"auto-risk-fleet-ceiling", "auto-contradiction-tick-rate"} <= ids
    assert {r["risk_id"] for r in stored} == {"auto-risk-fleet-ceiling", "auto-contradiction-tick-rate"}


@pytest.mark.asyncio
async def test_rerun_does_not_duplicate(tmp_path):
    store = SQLiteRiskStore(str(tmp_path / "app.db"))
    service = RiskDetectionService(
        document_store=StubDocStore(), risk_store=store,
        detector=StubDetector([FLEET, TICK]),
    )
    await service.detect_and_store()
    await service.detect_and_store()

    auto = [r for r in store.list() if r["risk_id"].startswith("auto-")]
    assert len(auto) == 2


@pytest.mark.asyncio
async def test_loads_one_document_per_filename(tmp_path):
    store = SQLiteRiskStore(str(tmp_path / "app.db"))
    summaries = [
        SimpleNamespace(filename="a.md", document_id="d1"),
        SimpleNamespace(filename="a.md", document_id="d2"),  # duplicate row
        SimpleNamespace(filename="b.md", document_id="d3"),
    ]
    docs = {
        "d1": SimpleNamespace(filename="a.md", original_text="A"),
        "d3": SimpleNamespace(filename="b.md", original_text="B"),
    }
    doc_store = StubDocStore(summaries, docs)
    detector = StubDetector([])

    service = RiskDetectionService(document_store=doc_store, risk_store=store, detector=detector)
    await service.detect_and_store()

    assert doc_store.fetched == ["d1", "d3"]  # first per filename; duplicate skipped
    assert [d.filename for d in detector.documents] == ["a.md", "b.md"]
