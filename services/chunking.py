import re

_HEADING_RE = re.compile(r"^#{1,6}\s+\S")


def chunk_text(text: str, chunk_size: int = 120, overlap: int = 30) -> list[str]:
    """Split text into retrieval chunks.

    Markdown-structured text is split on headings so each section (e.g. ``## 8. Data
    stores``) becomes its own chunk that carries its heading. This keeps a section that
    *answers* a question from being diluted by a passage that merely *mentions* its terms,
    and out-ranked at retrieval time. Text without headings falls back to a plain word window
    (unchanged behaviour).
    """
    lines = text.splitlines()

    if not any(_HEADING_RE.match(line) for line in lines):
        return _window(text.split(), chunk_size=chunk_size, overlap=overlap)

    chunks: list[str] = []

    for heading, body in _split_sections(lines):
        heading_words = heading.split()
        section_words = heading_words + body.split()

        if not section_words:
            continue

        if len(section_words) <= chunk_size:
            chunks.append(" ".join(section_words))
            continue

        # Long section: window the body and repeat the heading so each piece keeps its topic.
        budget = max(1, chunk_size - len(heading_words))

        for window in _window(body.split(), chunk_size=budget, overlap=overlap):
            chunks.append(" ".join(heading_words + window.split()))

    return chunks


def _split_sections(lines: list[str]) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    heading = ""
    body_lines: list[str] = []

    for line in lines:
        if _HEADING_RE.match(line):
            if heading or any(body_line.strip() for body_line in body_lines):
                sections.append((heading, "\n".join(body_lines)))

            heading = line.strip()
            body_lines = []
        else:
            body_lines.append(line)

    if heading or any(body_line.strip() for body_line in body_lines):
        sections.append((heading, "\n".join(body_lines)))

    return sections


def _window(words: list[str], chunk_size: int, overlap: int) -> list[str]:
    if not words:
        return []

    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 4)

    step = max(1, chunk_size - overlap)
    chunks: list[str] = []

    for start in range(0, len(words), step):
        chunk_words = words[start:start + chunk_size]

        if not chunk_words:
            continue

        chunks.append(" ".join(chunk_words))

        if start + chunk_size >= len(words):
            break

    return chunks
