"""Unit tests for the Ask view's citation grouping (frontend/views/ask.py)."""

import sys
from pathlib import Path

FRONTEND_DIR = str(Path(__file__).resolve().parents[2] / "frontend")
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from views import ask  # noqa: E402


def test_group_citations_dedupes_by_file_and_keeps_best_score():
    citations = [
        {"filename": "a.md", "snippet": "first", "hybrid_score": 0.40, "page_number": None},
        {"filename": "a.md", "snippet": "second", "hybrid_score": 0.80, "page_number": 3},
        {"filename": "b.pdf", "snippet": "other", "hybrid_score": 0.60, "page_number": 1},
    ]
    groups = ask._group_citations(citations)

    # Two distinct source files
    assert [g["filename"] for g in groups] == ["a.md", "b.pdf"]  # sorted by best score desc
    a = groups[0]
    assert a["best"] == 0.80
    assert a["page_number"] == 3  # page of the best-scoring chunk
    assert a["snippets"] == ["second", "first"]  # ordered by score desc


def test_group_citations_dedupes_identical_snippets():
    citations = [
        {"filename": "a.md", "snippet": "same", "hybrid_score": 0.5, "page_number": None},
        {"filename": "a.md", "snippet": "same", "hybrid_score": 0.7, "page_number": None},
    ]
    groups = ask._group_citations(citations)
    assert len(groups) == 1
    assert groups[0]["snippets"] == ["same"]
    assert groups[0]["best"] == 0.7


def test_group_citations_handles_empty():
    assert ask._group_citations([]) == []
