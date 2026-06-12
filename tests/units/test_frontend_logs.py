"""Unit tests for the Logs view's summary computation (frontend/views/logs.py)."""

import sys
from pathlib import Path

FRONTEND_DIR = str(Path(__file__).resolve().parents[2] / "frontend")
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from views import logs  # noqa: E402


def test_summary_aggregates_tokens_and_success_rate():
    rows = [
        {"input_tokens": 1000, "output_tokens": 200, "was_fallback": False},
        {"input_tokens": 500, "output_tokens": 100, "was_fallback": False},
        {"input_tokens": 50, "output_tokens": 0, "was_fallback": True},
    ]
    s = logs._summary(rows)
    assert s["stored"] == 3
    assert s["tokens"] == 1000 + 200 + 500 + 100 + 50
    assert s["avg_tokens"] == 617  # 1850 / 3, rounded
    assert s["success_rate"] == 67  # 2 of 3 answered without fallback


def test_summary_empty():
    s = logs._summary([])
    assert s == {"stored": 0, "tokens": 0, "avg_tokens": 0, "success_rate": 100}


def test_mode_badge_maps_provider_by_model():
    assert "Local" in logs._mode_badge("rule-based")
    assert "Gemini" in logs._mode_badge("gemini-2.5-flash")
    assert "Groq" in logs._mode_badge("llama-3.1-8b-instant")
    assert "gpt-4.1-mini" in logs._mode_badge("gpt-4.1-mini")


def test_csv_has_header_and_rows():
    csv_text = logs._to_csv([{"question": "q1", "estimated_cost_usd": 0.0008}])
    assert "question" in csv_text.splitlines()[0]
    assert "q1" in csv_text
