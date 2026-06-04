"""Unit tests for the Logs view's summary computation (frontend/views/logs.py)."""

import sys
from pathlib import Path

FRONTEND_DIR = str(Path(__file__).resolve().parents[2] / "frontend")
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from views import logs  # noqa: E402


def test_summary_aggregates_cost_tokens_and_fallback():
    rows = [
        {"estimated_cost_usd": 0.0008, "input_tokens": 1000,
         "output_tokens": 200, "was_fallback": False},
        {"estimated_cost_usd": 0.0004, "input_tokens": 500,
         "output_tokens": 100, "was_fallback": False},
        {"estimated_cost_usd": 0.0, "input_tokens": 50,
         "output_tokens": 0, "was_fallback": True},
    ]
    s = logs._summary(rows)
    assert s["stored"] == 3
    assert round(s["total_cost"], 4) == 0.0012
    assert s["tokens"] == 1000 + 200 + 500 + 100 + 50
    assert round(s["avg_cost"], 4) == 0.0004
    assert s["fallback_rate"] == 33  # 1 of 3


def test_summary_empty():
    s = logs._summary([])
    assert s == {"stored": 0, "total_cost": 0.0, "avg_cost": 0.0, "tokens": 0, "fallback_rate": 0}


def test_mode_badge_local_vs_openai():
    assert "Local" in logs._mode_badge("rule-based")
    assert "gpt-4.1-mini" in logs._mode_badge("gpt-4.1-mini")


def test_csv_has_header_and_rows():
    csv_text = logs._to_csv([{"question": "q1", "estimated_cost_usd": 0.0008}])
    assert "question" in csv_text.splitlines()[0]
    assert "q1" in csv_text
