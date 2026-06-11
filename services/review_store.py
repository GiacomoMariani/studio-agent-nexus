"""SQLAlchemy-backed store for reviews (board items).

The project's first SQLAlchemy model. Tables are created with `create_all` on store
construction (idempotent) — a migration tool (Alembic) is deferred until the schema must
evolve against a persistent DB. Reviews share the same SQLite file as the other stores
(`APP_DB_PATH`) but live in their own `reviews` table.

Identity is the caller-supplied `task_id` (primary key). `upsert` overwrites the record
when the same `task_id` is written again — there is no separate update operation.
"""

import os
from datetime import datetime, timezone

from sqlalchemy import String, create_engine, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from services.schema_guard import reconcile_table


class Base(DeclarativeBase):
    pass


class ReviewRow(Base):
    __tablename__ = "reviews"

    task_id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, default="")
    department: Mapped[str] = mapped_column(String)
    priority: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String, default="")
    state: Mapped[str] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String)


def _row_to_dict(row: ReviewRow) -> dict:
    return {
        "task_id": row.task_id,
        "title": row.title,
        "description": row.description,
        "department": row.department,
        "priority": row.priority,
        "source": row.source,
        "state": row.state,
        "updated_at": row.updated_at,
    }


class SQLiteReviewStore:
    def __init__(self, db_path: str = "app.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        reconcile_table(self.engine, ReviewRow)

    def upsert(
        self,
        *,
        task_id: str,
        title: str,
        description: str,
        department: str,
        priority: str,
        source: str,
        state: str,
    ) -> dict:
        """Insert or overwrite the review keyed on task_id; return the stored record."""
        updated_at = datetime.now(timezone.utc).isoformat()
        record = {
            "task_id": task_id,
            "title": title,
            "description": description,
            "department": department,
            "priority": priority,
            "source": source,
            "state": state,
            "updated_at": updated_at,
        }
        with Session(self.engine) as session:
            session.merge(ReviewRow(**record))  # merge = insert-or-update by primary key
            session.commit()
        return record

    def get(self, task_id: str) -> dict | None:
        with Session(self.engine) as session:
            row = session.get(ReviewRow, task_id)
            return _row_to_dict(row) if row is not None else None

    def list(self) -> list[dict]:
        """All reviews, newest write first."""
        with Session(self.engine) as session:
            rows = session.execute(
                select(ReviewRow).order_by(ReviewRow.updated_at.desc())
            ).scalars().all()
            return [_row_to_dict(row) for row in rows]

    def delete(self, task_id: str) -> bool:
        with Session(self.engine) as session:
            row = session.get(ReviewRow, task_id)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True

    def clear(self) -> None:
        with Session(self.engine) as session:
            session.execute(delete(ReviewRow))
            session.commit()


sqlite_review_store = SQLiteReviewStore(db_path=os.getenv("APP_DB_PATH", "app.db"))
