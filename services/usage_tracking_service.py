import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class UsageRecord:
    usage_id: str
    operation: str
    provider: str
    model_name: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    metadata: dict[str, str]
    created_at: str


@dataclass(frozen=True)
class UsageEstimate:
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float


@dataclass(frozen=True)
class UsagePricing:
    input_cost_per_1k_tokens_usd: float
    output_cost_per_1k_tokens_usd: float


class SQLiteUsageTrackingService:
    def __init__(
        self,
        db_path: str = "app.db",
        default_pricing: UsagePricing | None = None,
    ):
        self.db_path = db_path
        self.default_pricing = default_pricing or UsagePricing(
            input_cost_per_1k_tokens_usd=0.0,
            output_cost_per_1k_tokens_usd=0.0,
        )
        self._initialize()

    def _initialize(self) -> None:
        Path(self.db_path).touch(exist_ok=True)

        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_records (
                    usage_id TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    estimated_cost_usd REAL NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            connection.commit()

    def estimate_usage(
        self,
        input_text: str,
        output_text: str = "",
        pricing: UsagePricing | None = None,
    ) -> UsageEstimate:
        selected_pricing = pricing or self.default_pricing

        input_tokens = self._estimate_tokens(input_text)
        output_tokens = self._estimate_tokens(output_text)

        estimated_cost_usd = self._estimate_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            pricing=selected_pricing,
        )

        return UsageEstimate(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost_usd,
        )

    def record_usage(
        self,
        operation: str,
        provider: str,
        model_name: str,
        input_text: str,
        output_text: str = "",
        pricing: UsagePricing | None = None,
        metadata: dict[str, str] | None = None,
    ) -> UsageRecord:
        estimate = self.estimate_usage(
            input_text=input_text,
            output_text=output_text,
            pricing=pricing,
        )

        return self.record_usage_tokens(
            operation=operation,
            provider=provider,
            model_name=model_name,
            input_tokens=estimate.input_tokens,
            output_tokens=estimate.output_tokens,
            estimated_cost_usd=estimate.estimated_cost_usd,
            metadata=metadata,
        )

    def record_usage_tokens(
        self,
        operation: str,
        provider: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        estimated_cost_usd: float,
        metadata: dict[str, str] | None = None,
    ) -> UsageRecord:
        if input_tokens < 0:
            raise ValueError("input_tokens must be greater than or equal to 0.")

        if output_tokens < 0:
            raise ValueError("output_tokens must be greater than or equal to 0.")

        if estimated_cost_usd < 0:
            raise ValueError("estimated_cost_usd must be greater than or equal to 0.")

        usage_id = f"usage-{uuid4().hex[:12]}"
        created_at = self._now()
        clean_metadata = metadata or {}

        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO usage_records (
                    usage_id,
                    operation,
                    provider,
                    model_name,
                    input_tokens,
                    output_tokens,
                    estimated_cost_usd,
                    metadata_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    usage_id,
                    operation,
                    provider,
                    model_name,
                    input_tokens,
                    output_tokens,
                    estimated_cost_usd,
                    json.dumps(clean_metadata),
                    created_at,
                ),
            )

            connection.commit()

        return UsageRecord(
            usage_id=usage_id,
            operation=operation,
            provider=provider,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost_usd,
            metadata=clean_metadata,
            created_at=created_at,
        )

    def list_recent_usage(self, limit: int = 20) -> list[UsageRecord]:
        if limit <= 0:
            return []

        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    usage_id,
                    operation,
                    provider,
                    model_name,
                    input_tokens,
                    output_tokens,
                    estimated_cost_usd,
                    metadata_json,
                    created_at
                FROM usage_records
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )

            rows = cursor.fetchall()

        return [
            self._row_to_usage_record(row)
            for row in rows
        ]

    def get_total_estimated_cost_usd(self) -> float:
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT COALESCE(SUM(estimated_cost_usd), 0)
                FROM usage_records
                """
            )

            value = cursor.fetchone()[0]

        return round(float(value), 8)

    def clear(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM usage_records")
            connection.commit()

    def _estimate_tokens(self, text: str) -> int:
        cleaned = text.strip()

        if not cleaned:
            return 0

        return max(1, round(len(cleaned) / 4))

    def _estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        pricing: UsagePricing,
    ) -> float:
        input_cost = (
            input_tokens / 1000
        ) * pricing.input_cost_per_1k_tokens_usd

        output_cost = (
            output_tokens / 1000
        ) * pricing.output_cost_per_1k_tokens_usd

        return round(input_cost + output_cost, 8)

    def _row_to_usage_record(self, row: tuple[object, ...]) -> UsageRecord:
        return UsageRecord(
            usage_id=str(row[0]),
            operation=str(row[1]),
            provider=str(row[2]),
            model_name=str(row[3]),
            input_tokens=int(row[4]),
            output_tokens=int(row[5]),
            estimated_cost_usd=float(row[6]),
            metadata=json.loads(str(row[7])),
            created_at=str(row[8]),
        )

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()


sqlite_usage_tracking_service = SQLiteUsageTrackingService(
    db_path=os.getenv("APP_DB_PATH", "app.db")
)