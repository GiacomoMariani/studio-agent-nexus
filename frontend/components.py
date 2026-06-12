"""Shared UI components for Studio Agent Nexus.

Render helpers that emit the design-system markup. Functions named ``*_html`` return an
HTML string for inline composition; the rest render directly via Streamlit.
"""

from html import escape

import streamlit as st

# ---------------------------------------------------------------------------
# Inline badge helpers (return HTML strings)
# ---------------------------------------------------------------------------

def badge_html(label: str, cls: str) -> str:
    return f'<span class="badge {cls}">{escape(label)}</span>'


def dept_badge_html(dept: str) -> str:
    cls = escape(dept.lower())
    return f'<span class="badge badge--dept badge--{cls}">{escape(dept)}</span>'


def priority_badge_html(level: str) -> str:
    return f'<span class="badge badge--{escape(level.lower())}">{escape(level)}</span>'


# Jira draft helpers (ticket-017 / 018) — shared by the Board generator and the Ask page.
JIRA_STUB_MESSAGE = "Missing Project Manager pass — Jira sync not configured"
_ISSUE_BADGE_CLASS = {
    "Story": "badge--issue-story",
    "Task": "badge--issue-task",
    "Bug": "badge--issue-bug",
    "Epic": "badge--issue-epic",
}


def issue_type_badge(issue_type: str) -> str:
    return badge_html(issue_type, _ISSUE_BADGE_CLASS.get(issue_type, "badge--issue-task"))


def skill_badge_html(text: str) -> str:
    return f'<span class="skill-badge">{escape(text)}</span>'


def stat_card_html(label: str, value: str, tone: str = "white", sub: str | None = None) -> str:
    sub_html = (
        f'<div class="muted-caption" style="margin-top:4px">{escape(sub)}</div>' if sub else ""
    )
    return (
        f'<div class="stat-card"><div class="kicker">{escape(label)}</div>'
        f'<div class="stat-card__value stat-card__value--{tone}">{escape(str(value))}</div>'
        f"{sub_html}</div>"
    )


# ---------------------------------------------------------------------------
# Block components (render directly)
# ---------------------------------------------------------------------------

def page_header(title: str, sub: str) -> None:
    st.markdown(
        f'<header class="page-header">'
        f'<h1 class="page-header__title">{escape(title)}</h1>'
        f'<p class="page-header__sub">{escape(sub)}</p>'
        f"</header>",
        unsafe_allow_html=True,
    )


def fallback_notice(
    title: str = "Not found in uploaded documents",
    sub: str = "Upload the relevant doc to get a grounded answer.",
) -> None:
    icon = '<span style="color:var(--accent);font-size:1.4rem;line-height:1">⚠</span>'
    st.markdown(
        f'<div class="fallback">{icon}'
        f'<div><div class="fallback__title">{escape(title)}</div>'
        f'<div class="fallback__sub">{escape(sub)}</div></div></div>',
        unsafe_allow_html=True,
    )


def placeholder(message: str) -> None:
    st.markdown(f'<div class="placeholder">{escape(message)}</div>', unsafe_allow_html=True)


def toast(message: str, icon: str = "✅") -> None:
    st.toast(message, icon=icon)


# ---------------------------------------------------------------------------
# "How it works" footer
# ---------------------------------------------------------------------------

FOOTER_CONTENT: dict[str, dict] = {
    "upload": {
        "badges": ["Document Ingestion", "Chunking", "Embedding", "Vector Storage"],
        "text": (
            "When you upload a document, Studio Agent Nexus extracts the text, splits it "
            "into retrieval-friendly chunks, generates embeddings for each chunk, and "
            "stores them with metadata. This pipeline is the foundation of every grounded "
            "answer the agent produces."
        ),
    },
    "ask": {
        "badges": ["RAG Pipeline", "Hybrid Retrieval", "Citation Grounding", "Fallback Logic"],
        "text": (
            "Your question is embedded and scored against every chunk in the knowledge "
            "base using both vector similarity and keyword overlap. The top results are "
            "passed to the answerer. Every factual claim is traced to a source document. "
            "If confidence is too low, the agent falls back rather than inventing an answer."
        ),
    },
    "board": {
        "badges": [
            "Structured Output", "DB Persistence",
            "Upsert API", "Role-Based UX",
        ],
        "text": (
            "The board displays board items and planning suggestions that an external "
            "producer POSTs to the backend's reviews API, persisted in SQLite. Items are "
            "grouped by state and scoped to a source document; a planning suggestion can be "
            "promoted into a backlog item with one call. A single upsert endpoint both "
            "creates an item and moves it between states — re-posting the same id overwrites "
            "— so the producer drives the data while the UI stays a clean, role-aware view."
        ),
    },
    "risks": {
        "badges": ["Agentic Reasoning", "Contradiction Detection", "Citation Grounding"],
        "text": (
            "The agent scans across documents for inconsistencies and concerns. "
            "Contradictions are surfaced with both conflicting statements and their source "
            "documents, so a producer can make an informed decision rather than trusting a "
            "black-box summary."
        ),
    },
    "logs": {
        "badges": ["Observability", "Cost Tracking", "Audit Log", "Token Accounting"],
        "text": (
            "Every interaction is persisted with its question, the answer returned, the "
            "model used, and the exact token cost. A durable log like this is what lets a "
            "team audit what the agent has said, trace any answer back to its run, and keep "
            "spend under control as usage scales — the difference between a demo and a "
            "system you can actually operate."
        ),
    },
}


def page_footer(page: str) -> None:
    content = FOOTER_CONTENT.get(page)
    if not content:
        return

    st.markdown("<div style='margin-top:2.5rem'></div>", unsafe_allow_html=True)
    with st.expander("How it works"):
        badges = "".join(skill_badge_html(b) for b in content["badges"])
        st.markdown(
            f'<div style="margin-bottom:var(--sp-3)">{badges}</div>'
            f'<p class="footer-text">{escape(content["text"])}</p>',
            unsafe_allow_html=True,
        )
