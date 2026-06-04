"""Unit tests for SQLiteReviewStore (SQLAlchemy-backed, upsert by task_id)."""

import time

from services.review_store import SQLiteReviewStore

_REVIEW = {
    "task_id": "TASK-001",
    "title": "Reconcile matchmaking SLA target",
    "description": "15s vs 10s.",
    "department": "Backend",
    "priority": "Critical",
    "source": "release_readiness_checklist.md",
    "state": "ai",
}


def test_upsert_returns_record_with_timestamp(tmp_path):
    store = SQLiteReviewStore(str(tmp_path / "t.db"))
    record = store.upsert(**_REVIEW)

    assert record["task_id"] == "TASK-001"
    assert record["updated_at"]  # server-set
    assert "review_id" not in record  # identity is task_id
    assert record["state"] == "ai"


def test_upsert_same_task_id_overwrites(tmp_path):
    store = SQLiteReviewStore(str(tmp_path / "t.db"))
    store.upsert(**_REVIEW)
    store.upsert(**{**_REVIEW, "state": "done", "title": "Updated title"})

    # One row, overwritten — not two.
    rows = store.list()
    assert len(rows) == 1
    assert rows[0]["state"] == "done"
    assert rows[0]["title"] == "Updated title"


def test_get_returns_review(tmp_path):
    store = SQLiteReviewStore(str(tmp_path / "t.db"))
    store.upsert(**_REVIEW)
    assert store.get("TASK-001")["state"] == "ai"


def test_get_unknown_returns_none(tmp_path):
    store = SQLiteReviewStore(str(tmp_path / "t.db"))
    assert store.get("TASK-999") is None


def test_list_orders_newest_first(tmp_path):
    store = SQLiteReviewStore(str(tmp_path / "t.db"))
    store.upsert(**_REVIEW)  # TASK-001
    time.sleep(0.01)  # guarantee a distinct updated_at timestamp
    store.upsert(**{**_REVIEW, "task_id": "TASK-002"})
    rows = store.list()
    assert [r["task_id"] for r in rows] == ["TASK-002", "TASK-001"]  # newest write first


def test_delete_by_task_id(tmp_path):
    store = SQLiteReviewStore(str(tmp_path / "t.db"))
    store.upsert(**_REVIEW)
    assert store.delete("TASK-001") is True
    assert store.get("TASK-001") is None


def test_delete_unknown_returns_false(tmp_path):
    store = SQLiteReviewStore(str(tmp_path / "t.db"))
    assert store.delete("TASK-404") is False


def test_persists_across_store_instances(tmp_path):
    db = str(tmp_path / "t.db")
    SQLiteReviewStore(db).upsert(**_REVIEW)
    assert SQLiteReviewStore(db).get("TASK-001")["title"] == _REVIEW["title"]


def test_clear_empties_table(tmp_path):
    store = SQLiteReviewStore(str(tmp_path / "t.db"))
    store.upsert(**_REVIEW)
    store.clear()
    assert store.list() == []
