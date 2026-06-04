from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Protocol


class UploadedTextStore(Protocol):
    def save_text(self, filename: str, text: str) -> str:
        ...

    def get_text(self, content_id: str) -> str | None:
        ...

    def delete_text(self, content_id: str) -> bool:
        ...

    def delete_texts_created_before(self, cutoff: datetime) -> int:
        ...


class SQLiteUploadedTextStore:
    def __init__(self, db_path: str | Path = "uploaded_texts.db") -> None:
        self.db_path = Path(db_path)
        self._initialize_database()

    def save_text(self, filename: str, text: str) -> str:
        content_id = str(uuid.uuid4())

        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO uploaded_texts (content_id, filename, text)
                VALUES (?, ?, ?)
                """,
                (content_id, filename, text),
            )
            connection.commit()

        return content_id

    def get_text(self, content_id: str) -> str | None:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT text
                FROM uploaded_texts
                WHERE content_id = ?
                """,
                (content_id,),
            ).fetchone()

        if row is None:
            return None

        return row[0]

    def _initialize_database(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS uploaded_texts (
                    content_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.commit()

    def delete_text(self, content_id: str) -> bool:
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                DELETE
                FROM uploaded_texts
                WHERE content_id = ?
                """,
                (content_id,),
            )
            connection.commit()

        return cursor.rowcount > 0

    def delete_texts_created_before(self, cutoff: datetime) -> int:
        cutoff_value = cutoff.strftime("%Y-%m-%d %H:%M:%S")

        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                DELETE
                FROM uploaded_texts
                WHERE created_at < ?
                """,
                (cutoff_value,),
            )
            connection.commit()

        return cursor.rowcount