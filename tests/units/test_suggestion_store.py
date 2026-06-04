"""Unit tests for SQLiteSuggestionStore (SQLAlchemy-backed, upsert by suggestion_id)."""

import time

from services.planning_suggestion_store import SQLiteSuggestionStore

_SUGGESTION = {
    "suggestion_id": "SUG-001",
    "title": "Document the PII purge window",
    "reason": "Pipeline stores PII events with no deletion policy.",
    "department": "Data",
    "priority": "Critical",
    "source": "data_pipeline_spec.pdf",
}


def test_upsert_returns_record_with_timestamp(tmp_path):
    store = SQLiteSuggestionStore(str(tmp_path / "t.db"))
    record = store.upsert(**_SUGGESTION)

    assert record["suggestion_id"] == "SUG-001"
    assert record["updated_at"]
    assert record["department"] == "Data"


def test_upsert_same_id_overwrites(tmp_path):
    store = SQLiteSuggestionStore(str(tmp_path / "t.db"))
    store.upsert(**_SUGGESTION)
    store.upsert(**{**_SUGGESTION, "priority": "High", "title": "Updated"})

    rows = store.list()
    assert len(rows) == 1
    assert rows[0]["priority"] == "High"
    assert rows[0]["title"] == "Updated"


def test_get_and_delete(tmp_path):
    store = SQLiteSuggestionStore(str(tmp_path / "t.db"))
    store.upsert(**_SUGGESTION)
    assert store.get("SUG-001")["reason"].startswith("Pipeline")
    assert store.delete("SUG-001") is True
    assert store.get("SUG-001") is None


def test_delete_unknown_returns_false(tmp_path):
    store = SQLiteSuggestionStore(str(tmp_path / "t.db"))
    assert store.delete("SUG-404") is False


def test_list_orders_newest_first(tmp_path):
    store = SQLiteSuggestionStore(str(tmp_path / "t.db"))
    store.upsert(**_SUGGESTION)  # SUG-001
    time.sleep(0.01)
    store.upsert(**{**_SUGGESTION, "suggestion_id": "SUG-002"})
    assert [r["suggestion_id"] for r in store.list()] == ["SUG-002", "SUG-001"]


def test_persists_across_instances(tmp_path):
    db = str(tmp_path / "t.db")
    SQLiteSuggestionStore(db).upsert(**_SUGGESTION)
    assert SQLiteSuggestionStore(db).get("SUG-001")["title"] == _SUGGESTION["title"]
