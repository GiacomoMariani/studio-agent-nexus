import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class StoredRetrievedSource:
    source_id: str
    query_log_id: str
    chunk_id: str
    filename: str | None
    page_number: int | None
    snippet: str
    vector_score: float
    keyword_score: float
    hybrid_score: float
    rank: int


@dataclass(frozen=True)
class StoredDocumentQueryLog:
    query_log_id: str
    document_id: str
    question: str
    answer: str
    citation_count: int
    was_fallback: bool
    latency_ms: float
    created_at: str
    model_name: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    retrieved_sources: list[StoredRetrievedSource] = field(default_factory=list)


class SQLiteDocumentQueryLogStore:
    def __init__(self, db_path: str = "app.db"):
        self.db_path = db_path
        self._initialize()

    def _initialize(self) -> None:
        Path(self.db_path).touch(exist_ok=True)

        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS document_query_logs (
                    query_log_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    citation_count INTEGER NOT NULL,
                    was_fallback INTEGER NOT NULL DEFAULT 0,
                    latency_ms REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    model_name TEXT NOT NULL DEFAULT '',
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    estimated_cost_usd REAL NOT NULL DEFAULT 0
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS document_retrieved_sources (
                    source_id TEXT PRIMARY KEY,
                    query_log_id TEXT NOT NULL,
                    chunk_id TEXT NOT NULL,
                    filename TEXT,
                    page_number INTEGER,
                    snippet TEXT NOT NULL,
                    vector_score REAL NOT NULL,
                    keyword_score REAL NOT NULL,
                    hybrid_score REAL NOT NULL,
                    rank INTEGER NOT NULL,
                    FOREIGN KEY (query_log_id) REFERENCES document_query_logs(query_log_id)
                )
                """
            )

            self._ensure_query_log_columns(cursor)
            self._ensure_retrieved_source_columns(cursor)

            connection.commit()

    def record_query(
        self,
        document_id: str,
        question: str,
        answer: str,
        citation_count: int,
        was_fallback: bool,
        latency_ms: float,
        retrieved_sources: list[Any] | None = None,
        model_name: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
    ) -> StoredDocumentQueryLog:
        query_log_id = f"query-{uuid4().hex[:12]}"
        created_at = self._now()
        normalized_sources = self._normalize_retrieved_sources(
            query_log_id=query_log_id,
            retrieved_sources=retrieved_sources or [],
        )

        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO document_query_logs (
                    query_log_id,
                    document_id,
                    question,
                    answer,
                    citation_count,
                    was_fallback,
                    latency_ms,
                    created_at,
                    model_name,
                    input_tokens,
                    output_tokens,
                    estimated_cost_usd
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_log_id,
                    document_id,
                    question,
                    answer,
                    citation_count,
                    1 if was_fallback else 0,
                    latency_ms,
                    created_at,
                    model_name,
                    input_tokens,
                    output_tokens,
                    estimated_cost_usd,
                ),
            )

            for source in normalized_sources:
                cursor.execute(
                    """
                    INSERT INTO document_retrieved_sources (
                        source_id,
                        query_log_id,
                        chunk_id,
                        filename,
                        page_number,
                        snippet,
                        vector_score,
                        keyword_score,
                        hybrid_score,
                        rank
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source.source_id,
                        source.query_log_id,
                        source.chunk_id,
                        source.filename,
                        source.page_number,
                        source.snippet,
                        source.vector_score,
                        source.keyword_score,
                        source.hybrid_score,
                        source.rank,
                    ),
                )

            connection.commit()

        return StoredDocumentQueryLog(
            query_log_id=query_log_id,
            document_id=document_id,
            question=question,
            answer=answer,
            citation_count=citation_count,
            was_fallback=was_fallback,
            latency_ms=latency_ms,
            created_at=created_at,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost_usd,
            retrieved_sources=normalized_sources,
        )

    def get_recent_logs(self, limit: int = 20) -> list[StoredDocumentQueryLog]:
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    query_log_id,
                    document_id,
                    question,
                    answer,
                    citation_count,
                    was_fallback,
                    latency_ms,
                    created_at,
                    model_name,
                    input_tokens,
                    output_tokens,
                    estimated_cost_usd
                FROM document_query_logs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )

            log_rows = cursor.fetchall()

            if not log_rows:
                return []

            query_log_ids = [
                str(row[0])
                for row in log_rows
            ]

            source_rows = self._get_source_rows(
                cursor=cursor,
                query_log_ids=query_log_ids,
            )

        sources_by_query_log_id: dict[str, list[StoredRetrievedSource]] = {}

        for source_row in source_rows:
            source = self._row_to_retrieved_source(source_row)
            sources_by_query_log_id.setdefault(source.query_log_id, []).append(source)

        return [
            self._row_to_query_log(
                row=log_row,
                retrieved_sources=sources_by_query_log_id.get(str(log_row[0]), []),
            )
            for log_row in log_rows
        ]

    def get_fallback_logs(self, limit: int = 20) -> list[StoredDocumentQueryLog]:
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT query_log_id,
                       document_id,
                       question,
                       answer,
                       citation_count,
                       was_fallback,
                       latency_ms,
                       created_at,
                       model_name,
                       input_tokens,
                       output_tokens,
                       estimated_cost_usd
                FROM document_query_logs
                WHERE was_fallback = 1
                ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            )

            log_rows = cursor.fetchall()

            if not log_rows:
                return []

            query_log_ids = [
                str(row[0])
                for row in log_rows
            ]

            source_rows = self._get_source_rows(
                cursor=cursor,
                query_log_ids=query_log_ids,
            )

        sources_by_query_log_id: dict[str, list[StoredRetrievedSource]] = {}

        for source_row in source_rows:
            source = self._row_to_retrieved_source(source_row)
            sources_by_query_log_id.setdefault(source.query_log_id, []).append(source)

        return [
            self._row_to_query_log(
                row=log_row,
                retrieved_sources=sources_by_query_log_id.get(str(log_row[0]), []),
            )
            for log_row in log_rows
        ]

    def clear(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM document_retrieved_sources")
            cursor.execute("DELETE FROM document_query_logs")
            connection.commit()

    def _get_source_rows(
        self,
        cursor: sqlite3.Cursor,
        query_log_ids: list[str],
    ) -> list[tuple[object, ...]]:
        placeholders = ", ".join("?" for _ in query_log_ids)

        cursor.execute(
            f"""
            SELECT
                source_id,
                query_log_id,
                chunk_id,
                filename,
                page_number,
                snippet,
                vector_score,
                keyword_score,
                hybrid_score,
                rank
            FROM document_retrieved_sources
            WHERE query_log_id IN ({placeholders})
            ORDER BY query_log_id ASC, rank ASC
            """,
            query_log_ids,
        )

        return cursor.fetchall()

    def _normalize_retrieved_sources(
        self,
        query_log_id: str,
        retrieved_sources: list[Any],
    ) -> list[StoredRetrievedSource]:
        normalized_sources: list[StoredRetrievedSource] = []

        for index, source in enumerate(retrieved_sources, start=1):
            normalized_sources.append(
                StoredRetrievedSource(
                    source_id=f"source-{uuid4().hex[:12]}",
                    query_log_id=query_log_id,
                    chunk_id=str(self._get_value(source, "chunk_id", "")),
                    filename=self._get_optional_string(source, "filename"),
                    page_number=self._get_optional_int(source, "page_number"),
                    snippet=str(self._get_value(source, "snippet", "")),
                    vector_score=float(self._get_value(source, "vector_score", 0.0)),
                    keyword_score=float(self._get_value(source, "keyword_score", 0.0)),
                    hybrid_score=float(self._get_value(source, "hybrid_score", 0.0)),
                    rank=int(self._get_value(source, "rank", index)),
                )
            )

        return normalized_sources

    def _row_to_query_log(
        self,
        row: tuple[object, ...],
        retrieved_sources: list[StoredRetrievedSource],
    ) -> StoredDocumentQueryLog:
        return StoredDocumentQueryLog(
            query_log_id=str(row[0]),
            document_id=str(row[1]),
            question=str(row[2]),
            answer=str(row[3]),
            citation_count=int(row[4]),
            was_fallback=bool(row[5]),
            latency_ms=float(row[6]),
            created_at=str(row[7]),
            model_name=str(row[8]),
            input_tokens=int(row[9]),
            output_tokens=int(row[10]),
            estimated_cost_usd=float(row[11]),
            retrieved_sources=retrieved_sources,
        )

    def _row_to_retrieved_source(
        self,
        row: tuple[object, ...],
    ) -> StoredRetrievedSource:
        return StoredRetrievedSource(
            source_id=str(row[0]),
            query_log_id=str(row[1]),
            chunk_id=str(row[2]),
            filename=None if row[3] is None else str(row[3]),
            page_number=None if row[4] is None else int(row[4]),
            snippet=str(row[5]),
            vector_score=float(row[6]),
            keyword_score=float(row[7]),
            hybrid_score=float(row[8]),
            rank=int(row[9]),
        )

    def _ensure_query_log_columns(self, cursor: sqlite3.Cursor) -> None:
        existing_columns = self._get_columns(
            cursor=cursor,
            table_name="document_query_logs",
        )

        if "was_fallback" not in existing_columns:
            cursor.execute(
                """
                ALTER TABLE document_query_logs
                ADD COLUMN was_fallback INTEGER NOT NULL DEFAULT 0
                """
            )

        cost_columns = {
            "model_name": "TEXT NOT NULL DEFAULT ''",
            "input_tokens": "INTEGER NOT NULL DEFAULT 0",
            "output_tokens": "INTEGER NOT NULL DEFAULT 0",
            "estimated_cost_usd": "REAL NOT NULL DEFAULT 0",
        }
        for column_name, column_def in cost_columns.items():
            if column_name not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE document_query_logs ADD COLUMN {column_name} {column_def}"
                )

    def _ensure_retrieved_source_columns(self, cursor: sqlite3.Cursor) -> None:
        existing_columns = self._get_columns(
            cursor=cursor,
            table_name="document_retrieved_sources",
        )

        if "filename" not in existing_columns:
            cursor.execute(
                """
                ALTER TABLE document_retrieved_sources
                ADD COLUMN filename TEXT
                """
            )

        if "page_number" not in existing_columns:
            cursor.execute(
                """
                ALTER TABLE document_retrieved_sources
                ADD COLUMN page_number INTEGER
                """
            )

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

    def _get_value(
        self,
        source: Any,
        field_name: str,
        default: Any,
    ) -> Any:
        if isinstance(source, dict):
            return source.get(field_name, default)

        return getattr(source, field_name, default)

    def _get_optional_string(
        self,
        source: Any,
        field_name: str,
    ) -> str | None:
        value = self._get_value(source, field_name, None)

        if value is None:
            return None

        return str(value)

    def _get_optional_int(
        self,
        source: Any,
        field_name: str,
    ) -> int | None:
        value = self._get_value(source, field_name, None)

        if value is None:
            return None

        return int(value)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()


sqlite_document_query_log_store = SQLiteDocumentQueryLogStore(
    db_path=os.getenv("APP_DB_PATH", "app.db")
)