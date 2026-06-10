"""Light text-cleaning helpers for presenting chunk text as readable prose.

Chunk text retains the markdown (``##``, ``**``) and ``[Page N]`` markers from the source
document, which otherwise leak into citation snippets. These helpers strip those markers
and build clean, boundary-aware snippets. The cleaning is intentionally minimal — it
removes markup, it does not parse document structure.
"""

import re

_PAGE_MARKER = re.compile(r"\[Page\s+\d+\]", re.IGNORECASE)
# ATX heading markers ("## "). Chunk text is collapsed to a single line, so a heading
# marker can appear inline (after a space), not only at the start of the string. The
# leading boundary keeps "C#" and similar from being treated as a marker.
_HEADING_MARKER = re.compile(r"(?:^|(?<=\s))#{1,6}\s+")
# List bullets ("- ", "* ", "• ") at the start or after a space.
_LIST_BULLET = re.compile(r"(?:^|(?<=\s))[-*•]\s+")
# Emphasis / inline-code markers.
_EMPHASIS = re.compile(r"\*\*|\*|__|_|`")


def to_plain_text(text: str) -> str:
    """Strip markdown markers and ``[Page N]`` tags, then collapse whitespace."""
    if not text:
        return ""

    cleaned = _PAGE_MARKER.sub(" ", text)
    cleaned = _HEADING_MARKER.sub("", cleaned)
    cleaned = _LIST_BULLET.sub("", cleaned)
    cleaned = _EMPHASIS.sub("", cleaned)

    return " ".join(cleaned.split())


def make_snippet(text: str, limit: int = 160) -> str:
    """Clean ``text`` and truncate to ``limit`` chars on a word boundary.

    Appends an ellipsis when truncated; never cuts a word in half.
    """
    cleaned = to_plain_text(text)

    if len(cleaned) <= limit:
        return cleaned

    truncated = cleaned[:limit]
    last_space = truncated.rfind(" ")

    if last_space > 0:
        truncated = truncated[:last_space]

    return truncated.rstrip(" ,;:.") + "…"
