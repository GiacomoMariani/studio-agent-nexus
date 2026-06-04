"""Unit tests for SQLiteRiskStore + the Risks view scope helper."""

import sys
from pathlib import Path

from services.risk_store import SQLiteRiskStore

FRONTEND_DIR = str(Path(__file__).resolve().parents[2] / "frontend")
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from views import risks  # noqa: E402

_RISK = {
    "risk_id": "RISK-001",
    "kind": "risk",
    "severity": "Critical",
    "title": "Undocumented ceiling",
    "source": "server_fleet_runbook.pdf",
}


def test_store_upsert_and_overwrite(tmp_path):
    store = SQLiteRiskStore(str(tmp_path / "t.db"))
    store.upsert(**_RISK)
    store.upsert(**{**_RISK, "severity": "Low"})
    rows = store.list()
    assert len(rows) == 1
    assert rows[0]["severity"] == "Low"
    assert rows[0]["updated_at"]


def test_store_delete(tmp_path):
    store = SQLiteRiskStore(str(tmp_path / "t.db"))
    store.upsert(**_RISK)
    assert store.delete("RISK-001") is True
    assert store.get("RISK-001") is None
    assert store.delete("RISK-404") is False


def test_in_scope_risk_uses_source():
    risk = {"kind": "risk", "source": "a.pdf"}
    assert risks._in_scope(risk, risks.ALL_DOCS)
    assert risks._in_scope(risk, "a.pdf")
    assert not risks._in_scope(risk, "b.pdf")


def test_in_scope_contradiction_uses_both_files():
    contra = {"kind": "contradiction", "a_file": "a.pdf", "b_file": "b.pdf"}
    assert risks._in_scope(contra, "a.pdf")
    assert risks._in_scope(contra, "b.pdf")
    assert not risks._in_scope(contra, "c.pdf")
