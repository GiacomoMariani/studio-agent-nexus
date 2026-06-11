"""Schema-drift self-heal for the SQLAlchemy stores.

Reproduces the failure that 500'd the Board: a persisted `reviews` table created by an
earlier schema (`review_id`/`created_at`) survives `create_all()` unchanged, so queries
referencing the current `updated_at` column blow up. The store now reconciles on
construction — rebuilding an empty drifted table, refusing to drop a populated one.
"""

import sqlite3

import pytest

from services.review_store import SQLiteReviewStore

LEGACY_COLUMNS = (
    "review_id VARCHAR PRIMARY KEY, task_id VARCHAR, title VARCHAR, "
    "description VARCHAR, department VARCHAR, priority VARCHAR, "
    "source VARCHAR, state VARCHAR, created_at VARCHAR"
)

REVIEW = {
    "task_id": "TASK-1",
    "title": "t",
    "description": "",
    "department": "Backend",
    "priority": "High",
    "source": "",
    "state": "ai",
}


def _make_legacy_reviews(db_path: str, *, with_row: bool) -> None:
    """Create a pre-migration `reviews` table (no `updated_at`), optionally with a row."""
    con = sqlite3.connect(db_path)
    con.execute(f"CREATE TABLE reviews ({LEGACY_COLUMNS})")
    if with_row:
        con.execute(
            "INSERT INTO reviews VALUES "
            "('r1','TASK-1','t','d','Backend','High','s','ai','2020-01-01')"
        )
    con.commit()
    con.close()


def test_empty_drifted_table_is_rebuilt(tmp_path):
    db = str(tmp_path / "app.db")
    _make_legacy_reviews(db, with_row=False)

    store = SQLiteReviewStore(db)  # __init__ reconciles the legacy table

    assert store.list() == []  # querying updated_at no longer raises
    store.upsert(**REVIEW)
    assert store.list()[0]["updated_at"]


def test_populated_drifted_table_raises_instead_of_dropping(tmp_path):
    db = str(tmp_path / "app.db")
    _make_legacy_reviews(db, with_row=True)

    with pytest.raises(RuntimeError, match="Schema drift"):
        SQLiteReviewStore(db)

    # The row is left intact for a human to migrate.
    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 1
    con.close()


def test_in_sync_table_is_left_untouched(tmp_path):
    db = str(tmp_path / "app.db")
    SQLiteReviewStore(db).upsert(**REVIEW)

    # Re-opening must not rebuild (and wipe) a table that already matches the model.
    reopened = SQLiteReviewStore(db)
    assert [r["task_id"] for r in reopened.list()] == ["TASK-1"]
