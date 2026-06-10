from services.text_cleaning import make_snippet, to_plain_text


def test_to_plain_text_strips_markdown_and_page_markers():
    raw = "[Page 2] ## 4. Title **bold** and `code` text"
    assert to_plain_text(raw) == "4. Title bold and code text"


def test_to_plain_text_strips_inline_heading_and_bullets():
    cleaned = to_plain_text("intro text. ## Section - first - second")
    assert "##" not in cleaned
    assert cleaned == "intro text. Section first second"


def test_to_plain_text_does_not_strip_hash_without_space():
    # "C#" must not be mistaken for a heading marker.
    assert to_plain_text("Built in C# today") == "Built in C# today"


def test_to_plain_text_collapses_whitespace_and_handles_empty():
    assert to_plain_text("  a\n\n  b   c ") == "a b c"
    assert to_plain_text("") == ""


def test_make_snippet_returns_clean_short_text_unchanged():
    assert make_snippet("[Page 1] **Remote** work is allowed.") == "Remote work is allowed."


def test_make_snippet_truncates_on_word_boundary_with_ellipsis():
    text = "alpha beta gamma delta epsilon zeta eta theta"
    snippet = make_snippet(text, limit=20)

    assert snippet.endswith("…")
    body = snippet[:-1]
    assert text.startswith(body)  # only whole words from the source, no mid-word cut
    assert len(body) <= 20
    assert not body.endswith(" ")
