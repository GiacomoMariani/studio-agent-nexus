import sqlite3
from datetime import datetime

from services.uploaded_text_store import SQLiteUploadedTextStore


def test_sqlite_uploaded_text_store_saves_and_reads_text(tmp_path):
    store = SQLiteUploadedTextStore(tmp_path / "uploaded_texts.db")

    content_id = store.save_text(
        filename="guide.txt",
        text="FastAPI is the backend framework.",
    )

    assert content_id

    assert store.get_text(content_id) == "FastAPI is the backend framework."


def test_sqlite_uploaded_text_store_returns_none_for_missing_content(tmp_path):
    store = SQLiteUploadedTextStore(tmp_path / "uploaded_texts.db")

    assert store.get_text("missing-content-id") is None


def test_sqlite_uploaded_text_store_deletes_text(tmp_path):
    store = SQLiteUploadedTextStore(tmp_path / "uploaded_texts.db")

    content_id = store.save_text(
        filename="guide.txt",
        text="FastAPI is the backend framework.",
    )

    assert store.get_text(content_id) == "FastAPI is the backend framework."

    assert store.delete_text(content_id) is True
    assert store.get_text(content_id) is None
    assert store.delete_text(content_id) is False

def test_sqlite_uploaded_text_store_deletes_texts_created_before_cutoff(tmp_path):
    db_path = tmp_path / "uploaded_texts.db"
    store = SQLiteUploadedTextStore(db_path)

    old_content_id = store.save_text(
        filename="old-guide.txt",
        text="This upload is stale.",
    )
    fresh_content_id = store.save_text(
        filename="fresh-guide.txt",
        text="This upload is still eligible for processing.",
    )

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            UPDATE uploaded_texts
            SET created_at = ?
            WHERE content_id = ?
            """,
            ("2024-01-01 00:00:00", old_content_id),
        )
        connection.execute(
            """
            UPDATE uploaded_texts
            SET created_at = ?
            WHERE content_id = ?
            """,
            ("2024-01-03 00:00:00", fresh_content_id),
        )
        connection.commit()

    deleted_count = store.delete_texts_created_before(
        datetime(2024, 1, 2, 0, 0, 0),
    )

    assert deleted_count == 1
    assert store.get_text(old_content_id) is None
    assert store.get_text(fresh_content_id) == "This upload is still eligible for processing."