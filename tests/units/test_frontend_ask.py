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


def test_group_citations_carries_document_id_for_download():
    citations = [
        {"filename": "a.md", "document_id": "doc-1", "snippet": "x", "hybrid_score": 0.9},
        {"filename": "a.md", "document_id": "doc-1", "snippet": "y", "hybrid_score": 0.5},
    ]
    groups = ask._group_citations(citations)
    assert groups[0]["document_id"] == "doc-1"


def test_group_citations_handles_empty():
    assert ask._group_citations([]) == []


def test_group_citations_collects_source_ids_per_file():
    citations = [
        {"filename": "a.md", "snippet": "one", "hybrid_score": 0.4,
         "page_number": None, "source_id": 1},
        {"filename": "a.md", "snippet": "two", "hybrid_score": 0.8,
         "page_number": None, "source_id": 2},
        {"filename": "b.pdf", "snippet": "three", "hybrid_score": 0.6,
         "page_number": 1, "source_id": 3},
    ]
    groups = ask._group_citations(citations)
    by_file = {g["filename"]: g["source_ids"] for g in groups}

    assert by_file["a.md"] == [1, 2]
    assert by_file["b.pdf"] == [3]


def test_score_breakdown_shows_each_retrieval_type():
    label = ask._score_breakdown(
        {
            "source_id": 3,
            "vector_score": 1.0,
            "keyword_score": 0.5,
            "hybrid_score": 0.85,
        }
    )
    assert "[3]" in label
    assert "vector 100%" in label
    assert "keyword 50%" in label
    assert "hybrid 85%" in label


def test_group_citations_keeps_each_passage_with_scores():
    citations = [
        {"filename": "a.md", "snippet": "one", "source_id": 1,
         "vector_score": 1.0, "keyword_score": 0.4, "hybrid_score": 0.8, "page_number": 2},
        {"filename": "a.md", "snippet": "two", "source_id": 2,
         "vector_score": 0.5, "keyword_score": 0.2, "hybrid_score": 0.4, "page_number": 3},
    ]
    passages = ask._group_citations(citations)[0]["passages"]

    assert [passage["source_id"] for passage in passages] == [1, 2]
    assert passages[0]["snippet"] == "one"
    assert passages[0]["vector_score"] == 1.0


def test_snippets_shown_defaults_to_three(monkeypatch):
    monkeypatch.delenv("SOURCE_SNIPPETS_SHOWN", raising=False)
    assert ask._snippets_shown() == 3


def test_snippets_shown_reads_env(monkeypatch):
    monkeypatch.setenv("SOURCE_SNIPPETS_SHOWN", "5")
    assert ask._snippets_shown() == 5


def test_snippets_shown_rejects_invalid_values(monkeypatch):
    monkeypatch.setenv("SOURCE_SNIPPETS_SHOWN", "not-a-number")
    assert ask._snippets_shown() == 3
    monkeypatch.setenv("SOURCE_SNIPPETS_SHOWN", "0")
    assert ask._snippets_shown() == 3
    monkeypatch.setenv("SOURCE_SNIPPETS_SHOWN", "-2")
    assert ask._snippets_shown() == 3


def test_provider_badge_reflects_configured_provider():
    assert "Gemini" in ask._provider_badge("gemini")
    assert "Groq" in ask._provider_badge("groq")
    assert "OpenAI" in ask._provider_badge("openai")
    assert "Rule-based" in ask._provider_badge("local")


def test_pick_pending_question_blocks_while_running():
    # A running query must block any new submission (typed or demo click).
    assert ask._pick_pending_question(True, True, "typed q", None) is None
    assert ask._pick_pending_question(True, False, "", "demo q") is None


def test_pick_pending_question_picks_typed_then_sample():
    assert ask._pick_pending_question(False, True, "  typed q  ", None) == "typed q"
    assert ask._pick_pending_question(False, False, "", "demo q") == "demo q"


def test_pick_pending_question_ignores_empty_submission():
    assert ask._pick_pending_question(False, True, "   ", None) is None
    assert ask._pick_pending_question(False, False, "", None) is None
