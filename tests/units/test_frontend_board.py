"""Unit tests for the Board view's sorting (frontend/views/board.py)."""

import sys
from pathlib import Path

FRONTEND_DIR = str(Path(__file__).resolve().parents[2] / "frontend")
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from views import board  # noqa: E402


def test_sort_orders_by_priority_then_recency():
    items = [
        {"task_id": "a", "priority": "Low", "updated_at": "2026-01-01"},
        {"task_id": "b", "priority": "Critical", "updated_at": "2026-01-01"},
        {"task_id": "c", "priority": "Critical", "updated_at": "2026-02-01"},
        {"task_id": "d", "priority": "High", "updated_at": "2026-01-01"},
    ]
    ordered = [r["task_id"] for r in board._sort_items(items)]
    # Critical first (newest of the two Criticals first), then High, then Low.
    assert ordered == ["c", "b", "d", "a"]


def test_sort_handles_unknown_priority_last():
    items = [
        {"task_id": "x", "priority": "Mystery", "updated_at": "2026-01-01"},
        {"task_id": "y", "priority": "High", "updated_at": "2026-01-01"},
    ]
    ordered = [r["task_id"] for r in board._sort_items(items)]
    assert ordered == ["y", "x"]


def test_sort_empty():
    assert board._sort_items([]) == []


def test_issue_badge_maps_each_type():
    assert "badge--issue-story" in board._issue_badge("Story")
    assert "badge--issue-bug" in board._issue_badge("Bug")
    # Unknown issue type falls back to the task badge rather than breaking.
    assert "badge--issue-task" in board._issue_badge("Mystery")


def test_resolve_scope_document_id():
    documents = [
        {"filename": "a.md", "document_id": "d1"},
        {"filename": "b.pdf", "document_id": "d2"},
    ]
    assert board._resolve_scope_document_id(board.ALL_DOCS, documents) is None
    assert board._resolve_scope_document_id("b.pdf", documents) == "d2"
    # A filename not present resolves to None (treated as no specific scope).
    assert board._resolve_scope_document_id("missing.md", documents) is None
