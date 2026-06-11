import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from services.document_store import StoredChunk, StoredDocument, StoredDocumentSummary


class SQLiteDocumentStore:
    def __init__(self, db_path: str = "app.db"):
        self.db_path = db_path
        self._initialize()

    def _initialize(self) -> None:
        Path(self.db_path).touch(exist_ok=True)

        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    original_text TEXT NOT NULL,
                    file_type TEXT NOT NULL DEFAULT 'unknown',
                    upload_date TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'indexed',
                    page_count INTEGER,
                    is_demo INTEGER NOT NULL DEFAULT 0
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    page_number INTEGER,
                    FOREIGN KEY (document_id) REFERENCES documents(document_id)
                )
                """
            )

            self._ensure_document_columns(cursor)
            self._ensure_chunk_columns(cursor)

            connection.commit()

    def save_document(
        self,
        filename: str,
        text: str,
        chunk_payloads: list[dict[str, object]],
        is_demo: bool = False,
    ) -> StoredDocument:
        document_id = f"doc-{uuid4().hex[:12]}"
        file_type = self._infer_file_type(filename)
        upload_date = self._now()
        status = "indexed"
        page_count = self._infer_page_count(chunk_payloads)

        chunks: list[StoredChunk] = []

        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO documents (document_id,
                                       filename,
                                       original_text,
                                       file_type,
                                       upload_date,
                                       status,
                                       page_count,
                                       is_demo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    filename,
                    text,
                    file_type,
                    upload_date,
                    status,
                    page_count,
                    1 if is_demo else 0,
                ),
            )

            for index, chunk_payload in enumerate(chunk_payloads, start=1):
                chunk_id = f"{document_id}-chunk-{index}"
                chunk_text = str(chunk_payload["text"])
                chunk_embedding = chunk_payload["embedding"]
                page_number = chunk_payload.get("page_number")

                cursor.execute(
                    """
                    INSERT INTO chunks (chunk_id,
                                        document_id,
                                        text,
                                        embedding,
                                        page_number)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        chunk_id,
                        document_id,
                        chunk_text,
                        json.dumps(chunk_embedding),
                        page_number,
                    ),
                )

                chunks.append(
                    StoredChunk(
                        chunk_id=chunk_id,
                        text=chunk_text,
                        embedding=chunk_embedding,
                        page_number=page_number,
                    )
                )

            connection.commit()

        return StoredDocument(
            document_id=document_id,
            filename=filename,
            original_text=text,
            file_type=file_type,
            upload_date=upload_date,
            status=status,
            page_count=page_count,
            chunks=chunks,
            is_demo=is_demo,
        )

    def get_document(self, document_id: str) -> StoredDocument | None:
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT document_id,
                       filename,
                       original_text,
                       file_type,
                       upload_date,
                       status,
                       page_count,
                       is_demo
                FROM documents
                WHERE document_id = ?
                """,
                (document_id,),
            )
            document_row = cursor.fetchone()

            if document_row is None:
                return None

            cursor.execute(
                """
                SELECT chunk_id, text, embedding, page_number
                FROM chunks
                WHERE document_id = ?
                ORDER BY rowid
                """,
                (document_id,),
            )
            chunk_rows = cursor.fetchall()

        chunks = [
            StoredChunk(
                chunk_id=chunk_id,
                text=text,
                embedding=json.loads(embedding),
                page_number=page_number,
            )
            for chunk_id, text, embedding, page_number in chunk_rows
        ]

        return StoredDocument(
            document_id=document_row[0],
            filename=document_row[1],
            original_text=document_row[2],
            file_type=document_row[3] or "unknown",
            upload_date=document_row[4] or self._now(),
            status=document_row[5] or "indexed",
            page_count=document_row[6],
            chunks=chunks,
            is_demo=bool(document_row[7]),
        )

    def delete_document(self, document_id: str, *, force: bool = False) -> bool:
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT is_demo
                FROM documents
                WHERE document_id = ?
                """,
                (document_id,),
            )

            row = cursor.fetchone()

            if row is None:
                return False

            # Demo docs are protected from API/user deletion; only trusted internal
            # callers (the seeder re-seeding from source) pass force=True to drop them.
            if bool(row[0]) and not force:
                return False

            cursor.execute(
                "DELETE FROM chunks WHERE document_id = ?",
                (document_id,),
            )
            cursor.execute(
                "DELETE FROM documents WHERE document_id = ?",
                (document_id,),
            )

            connection.commit()

        return True

    def replace_document_chunks(
        self,
        document_id: str,
        chunk_payloads: list[dict[str, object]],
    ) -> StoredDocument | None:
        chunks: list[StoredChunk] = []
        page_count = self._infer_page_count(chunk_payloads)

        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT filename,
                       original_text,
                       file_type,
                       upload_date,
                       status,
                       is_demo
                FROM documents
                WHERE document_id = ?
                """,
                (document_id,),
            )

            document_row = cursor.fetchone()

            if document_row is None:
                return None

            filename = document_row[0]
            original_text = document_row[1]
            file_type = document_row[2] or self._infer_file_type(filename)
            upload_date = document_row[3] or self._now()
            status = "indexed"
            is_demo = bool(document_row[5])

            cursor.execute(
                """
                DELETE
                FROM chunks
                WHERE document_id = ?
                """,
                (document_id,),
            )

            cursor.execute(
                """
                UPDATE documents
                SET status     = ?,
                    page_count = ?
                WHERE document_id = ?
                """,
                (status, page_count, document_id),
            )

            for index, chunk_payload in enumerate(chunk_payloads, start=1):
                chunk_id = f"{document_id}-chunk-{index}"
                chunk_text = str(chunk_payload["text"])
                chunk_embedding = chunk_payload["embedding"]
                page_number = chunk_payload.get("page_number")

                cursor.execute(
                    """
                    INSERT INTO chunks (chunk_id,
                                        document_id,
                                        text,
                                        embedding,
                                        page_number)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        chunk_id,
                        document_id,
                        chunk_text,
                        json.dumps(chunk_embedding),
                        page_number,
                    ),
                )

                chunks.append(
                    StoredChunk(
                        chunk_id=chunk_id,
                        text=chunk_text,
                        embedding=chunk_embedding,
                        page_number=page_number,
                    )
                )

            connection.commit()

        return StoredDocument(
            document_id=document_id,
            filename=filename,
            original_text=original_text,
            file_type=file_type,
            upload_date=upload_date,
            status=status,
            page_count=page_count,
            chunks=chunks,
            is_demo=is_demo,
        )

    def list_documents(self) -> list[StoredDocumentSummary]:
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT documents.document_id,
                       documents.filename,
                       documents.file_type,
                       documents.upload_date,
                       documents.status,
                       documents.page_count,
                       documents.is_demo,
                       COUNT(chunks.chunk_id) AS chunk_count
                FROM documents
                         LEFT JOIN chunks
                                   ON chunks.document_id = documents.document_id
                GROUP BY documents.document_id,
                         documents.filename,
                         documents.file_type,
                         documents.upload_date,
                         documents.status,
                         documents.page_count,
                         documents.is_demo
                ORDER BY documents.rowid
                """
            )

            rows = cursor.fetchall()

        return [
            StoredDocumentSummary(
                document_id=document_id,
                filename=filename,
                file_type=file_type or "unknown",
                upload_date=upload_date or self._now(),
                status=status or "indexed",
                page_count=page_count,
                chunk_count=chunk_count,
                is_demo=bool(is_demo),
            )
            for (
                document_id,
                filename,
                file_type,
                upload_date,
                status,
                page_count,
                is_demo,
                chunk_count,
            ) in rows
        ]

    def clear(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM chunks")
            cursor.execute("DELETE FROM documents")
            connection.commit()

    def _ensure_document_columns(self, cursor: sqlite3.Cursor) -> None:
        existing_columns = self._get_columns(
            cursor=cursor,
            table_name="documents",
        )

        if "file_type" not in existing_columns:
            cursor.execute(
                """
                ALTER TABLE documents
                    ADD COLUMN file_type TEXT NOT NULL DEFAULT 'unknown'
                """
            )

        if "upload_date" not in existing_columns:
            cursor.execute(
                """
                ALTER TABLE documents
                    ADD COLUMN upload_date TEXT NOT NULL DEFAULT ''
                """
            )

        if "status" not in existing_columns:
            cursor.execute(
                """
                ALTER TABLE documents
                    ADD COLUMN status TEXT NOT NULL DEFAULT 'indexed'
                """
            )

        if "page_count" not in existing_columns:
            cursor.execute(
                """
                ALTER TABLE documents
                    ADD COLUMN page_count INTEGER
                """
            )

        if "is_demo" not in existing_columns:
            cursor.execute(
                """
                ALTER TABLE documents
                    ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0
                """
            )

    def _ensure_chunk_columns(self, cursor: sqlite3.Cursor) -> None:
        existing_columns = self._get_columns(
            cursor=cursor,
            table_name="chunks",
        )

        if "page_number" not in existing_columns:
            cursor.execute("ALTER TABLE chunks ADD COLUMN page_number INTEGER")

    def _get_columns(
        self,
        cursor: sqlite3.Cursor,
        table_name: str,
    ) -> set[str]:
        cursor.execute(f"PRAGMA table_info({table_name})")

        return {
            str(row[1])
            for row in cursor.fetchall()
        }

    def _infer_file_type(self, filename: str) -> str:
        suffix = Path(filename).suffix.lower().lstrip(".")

        if suffix:
            return suffix

        return "unknown"

    def _infer_page_count(
        self,
        chunk_payloads: list[dict[str, object]],
    ) -> int | None:
        page_numbers = [
            int(chunk_payload["page_number"])
            for chunk_payload in chunk_payloads
            if chunk_payload.get("page_number") is not None
        ]

        if not page_numbers:
            return None

        return max(page_numbers)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()


sqlite_document_store = SQLiteDocumentStore(
    db_path=os.getenv("APP_DB_PATH", "app.db")
)