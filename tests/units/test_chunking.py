from services.chunking import chunk_text


def test_chunk_text_plain_text_uses_word_window():
    # No markdown headings → unchanged single-window behaviour for short text.
    chunks = chunk_text("FastAPI is the backend framework used in this project.")

    assert chunks == ["FastAPI is the backend framework used in this project."]


def test_chunk_text_empty_returns_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_splits_on_markdown_headings():
    text = (
        "# Title\n"
        "## 1. Purpose\n"
        "This document covers the data stores behind them.\n"
        "## 8. Data stores\n"
        "- Operational SQL for accounts.\n"
        "- Redis-style cache for sessions.\n"
    )
    chunks = chunk_text(text)

    # The section that lists the stores is one self-contained chunk carrying its heading.
    data_store_chunks = [chunk for chunk in chunks if "Data stores" in chunk]
    assert len(data_store_chunks) == 1
    section = data_store_chunks[0]
    assert "## 8. Data stores" in section
    assert "Operational SQL" in section
    assert "Redis-style cache" in section

    # The §1 passing mention is a separate chunk and does not absorb §8's content.
    purpose_chunks = [chunk for chunk in chunks if "1. Purpose" in chunk]
    assert all("Operational SQL" not in chunk for chunk in purpose_chunks)


def test_chunk_text_long_section_repeats_heading():
    body = " ".join(f"word{index}" for index in range(300))
    chunks = chunk_text(f"## 8. Data stores\n{body}", chunk_size=120, overlap=20)

    assert len(chunks) > 1
    # Every piece of a long section keeps its heading so the topic is retained.
    assert all(chunk.startswith("## 8. Data stores") for chunk in chunks)
