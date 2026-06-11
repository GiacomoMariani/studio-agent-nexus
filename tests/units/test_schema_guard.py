"""Schema-drift self-heal for the SQLAlchemy stores.

Reproduces the failure that 500'd the Board: a persisted `reviews` table created by an
earlier schema (`review_id`/`created_at`) survives `create_all()` unchanged, so queries
referencing the current `updated_at` column blow up. The store now reconciles on
construction — rebuilding an empty drifted table, refusing to drop a populated one.
"""

import sqlite3

import pytest

from services.review_store import SQLiteReviewStore
from services.risk_store import SQLiteRiskStore

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


# --- risks store (ticket-014): same guard, same three behaviours ---

# Pre-migration `risks` table: no `updated_at`, no contradiction fields, a stale `created_at`.
LEGACY_RISK_COLUMNS = (
    "risk_id VARCHAR PRIMARY KEY, kind VARCHAR, severity VARCHAR, "
    "title VARCHAR, description VARCHAR, source VARCHAR, created_at VARCHAR"
)

RISK = {
    "risk_id": "RISK-1",
    "kind": "risk",
    "severity": "High",
    "title": "t",
    "description": "d",
    "source": "s",
}


def _make_legacy_risks(db_path: str, *, with_row: bool) -> None:
    con = sqlite3.connect(db_path)
    con.execute(f"CREATE TABLE risks ({LEGACY_RISK_COLUMNS})")
    if with_row:
        con.execute("INSERT INTO risks VALUES ('RISK-1','risk','High','t','d','s','2020-01-01')")
    con.commit()
    con.close()


def test_empty_drifted_risks_table_is_rebuilt(tmp_path):
    db = str(tmp_path / "app.db")
    _make_legacy_risks(db, with_row=False)

    store = SQLiteRiskStore(db)

    assert store.list() == []  # querying updated_at / a_file no longer raises
    store.upsert(**RISK)
    assert store.list()[0]["updated_at"]


def test_populated_drifted_risks_table_raises_instead_of_dropping(tmp_path):
    db = str(tmp_path / "app.db")
    _make_legacy_risks(db, with_row=True)

    with pytest.raises(RuntimeError, match="Schema drift"):
        SQLiteRiskStore(db)

    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM risks").fetchone()[0] == 1
    con.close()


def test_in_sync_risks_table_is_left_untouched(tmp_path):
    db = str(tmp_path / "app.db")
    SQLiteRiskStore(db).upsert(**RISK)

    reopened = SQLiteRiskStore(db)
    assert [r["risk_id"] for r in reopened.list()] == ["RISK-1"]
