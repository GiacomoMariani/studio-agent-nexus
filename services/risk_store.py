"""SQLAlchemy-backed store for risk / contradiction findings.

Mirrors the reviews store: upsert keyed on the caller-supplied ``risk_id``, a single
server-set ``updated_at``, ``create_all`` on construction. Own ``risks`` table in the
shared ``APP_DB_PATH`` SQLite file. Findings only ever enter via POST.
"""

import os
from datetime import datetime, timezone

from sqlalchemy import String, create_engine, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class RiskRow(Base):
    __tablename__ = "risks"

    risk_id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, default="")
    source: Mapped[str] = mapped_column(String, default="")
    a_file: Mapped[str] = mapped_column(String, default="")
    a_text: Mapped[str] = mapped_column(String, default="")
    b_file: Mapped[str] = mapped_column(String, default="")
    b_text: Mapped[str] = mapped_column(String, default="")
    updated_at: Mapped[str] = mapped_column(String)


def _row_to_dict(row: RiskRow) -> dict:
    return {
        "risk_id": row.risk_id,
        "kind": row.kind,
        "severity": row.severity,
        "title": row.title,
        "description": row.description,
        "source": row.source,
        "a_file": row.a_file,
        "a_text": row.a_text,
        "b_file": row.b_file,
        "b_text": row.b_text,
        "updated_at": row.updated_at,
    }


class SQLiteRiskStore:
    def __init__(self, db_path: str = "app.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)

    def upsert(
        self,
        *,
        risk_id: str,
        kind: str,
        severity: str,
        title: str,
        description: str = "",
        source: str = "",
        a_file: str = "",
        a_text: str = "",
        b_file: str = "",
        b_text: str = "",
    ) -> dict:
        updated_at = datetime.now(timezone.utc).isoformat()
        record = {
            "risk_id": risk_id,
            "kind": kind,
            "severity": severity,
            "title": title,
            "description": description,
            "source": source,
            "a_file": a_file,
            "a_text": a_text,
            "b_file": b_file,
            "b_text": b_text,
            "updated_at": updated_at,
        }
        with Session(self.engine) as session:
            session.merge(RiskRow(**record))
            session.commit()
        return record

    def get(self, risk_id: str) -> dict | None:
        with Session(self.engine) as session:
            row = session.get(RiskRow, risk_id)
            return _row_to_dict(row) if row is not None else None

    def list(self) -> list[dict]:
        with Session(self.engine) as session:
            rows = session.execute(
                select(RiskRow).order_by(RiskRow.updated_at.desc())
            ).scalars().all()
            return [_row_to_dict(row) for row in rows]

    def delete(self, risk_id: str) -> bool:
        with Session(self.engine) as session:
            row = session.get(RiskRow, risk_id)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True

    def clear(self) -> None:
        with Session(self.engine) as session:
            session.execute(delete(RiskRow))
            session.commit()


sqlite_risk_store = SQLiteRiskStore(db_path=os.getenv("APP_DB_PATH", "app.db"))
