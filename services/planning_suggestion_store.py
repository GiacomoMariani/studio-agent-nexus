"""SQLAlchemy-backed store for planning suggestions ("tasks you may still need").

Mirrors the reviews store: upsert keyed on the caller-supplied `suggestion_id`, a single
server-set `updated_at`, `create_all` on construction. Lives in its own
`planning_suggestions` table in the shared `APP_DB_PATH` SQLite file.
"""

import os
from datetime import datetime, timezone

from sqlalchemy import String, create_engine, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class SuggestionRow(Base):
    __tablename__ = "planning_suggestions"

    suggestion_id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(String, default="")
    department: Mapped[str] = mapped_column(String)
    priority: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String, default="")
    updated_at: Mapped[str] = mapped_column(String)


def _row_to_dict(row: SuggestionRow) -> dict:
    return {
        "suggestion_id": row.suggestion_id,
        "title": row.title,
        "reason": row.reason,
        "department": row.department,
        "priority": row.priority,
        "source": row.source,
        "updated_at": row.updated_at,
    }


class SQLiteSuggestionStore:
    def __init__(self, db_path: str = "app.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)

    def upsert(
        self,
        *,
        suggestion_id: str,
        title: str,
        reason: str,
        department: str,
        priority: str,
        source: str,
    ) -> dict:
        updated_at = datetime.now(timezone.utc).isoformat()
        record = {
            "suggestion_id": suggestion_id,
            "title": title,
            "reason": reason,
            "department": department,
            "priority": priority,
            "source": source,
            "updated_at": updated_at,
        }
        with Session(self.engine) as session:
            session.merge(SuggestionRow(**record))  # insert-or-update by primary key
            session.commit()
        return record

    def get(self, suggestion_id: str) -> dict | None:
        with Session(self.engine) as session:
            row = session.get(SuggestionRow, suggestion_id)
            return _row_to_dict(row) if row is not None else None

    def list(self) -> list[dict]:
        with Session(self.engine) as session:
            rows = session.execute(
                select(SuggestionRow).order_by(SuggestionRow.updated_at.desc())
            ).scalars().all()
            return [_row_to_dict(row) for row in rows]

    def delete(self, suggestion_id: str) -> bool:
        with Session(self.engine) as session:
            row = session.get(SuggestionRow, suggestion_id)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True

    def clear(self) -> None:
        with Session(self.engine) as session:
            session.execute(delete(SuggestionRow))
            session.commit()


sqlite_suggestion_store = SQLiteSuggestionStore(db_path=os.getenv("APP_DB_PATH", "app.db"))
