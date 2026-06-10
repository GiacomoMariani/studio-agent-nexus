"""Ask page — grounded Q&A wired to the real document backend."""

from html import escape
from typing import Any

import api
import streamlit as st
from components import badge_html, fallback_notice, page_footer, page_header
from fixtures import SAMPLE_QUESTIONS

TOP_K = 5


def _group_citations(citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group citations by source file, keeping best score and de-duped snippets."""
    groups: dict[str, dict[str, Any]] = {}
    for cite in citations:
        filename = cite.get("filename", "Unknown source")
        score = cite.get("hybrid_score")
        score = score if isinstance(score, (int, float)) else None
        snippet = (cite.get("snippet") or "").strip()

        group = groups.setdefault(
            filename,
            {
                "filename": filename,
                "page_number": cite.get("page_number"),
                "best": None,
                "snips": [],
            },
        )
        if snippet and snippet not in [s for _, s in group["snips"]]:
            group["snips"].append((score if score is not None else -1.0, snippet))
        if score is not None and (group["best"] is None or score > group["best"]):
            group["best"] = score
            group["page_number"] = cite.get("page_number")

    result = []
    for group in groups.values():
        group["snips"].sort(key=lambda pair: pair[0], reverse=True)
        group["snippets"] = [s for _, s in group["snips"]]
        result.append(group)
    result.sort(key=lambda g: (g["best"] is not None, g["best"] or 0.0), reverse=True)
    return result


def _score_label(best: float) -> str:
    # Relative match within this result set (min-max normalised), not an absolute score.
    return f"Relative match: {best * 100:.0f}%"


def _run_query(question: str) -> None:
    cleaned = question.strip()
    if not cleaned:
        st.warning("Enter a question before asking.")
        return
    try:
        with st.spinner("Retrieving sources and generating an answer…"):
            response = api.ask_documents(cleaned, top_k=TOP_K)
    except api.ApiError as exc:
        st.session_state["last_answer"] = None
        st.session_state["last_error"] = str(exc)
        return
    st.session_state["last_error"] = None
    st.session_state["last_answer"] = {
        "question": cleaned,
        "answer": response.get("answer", ""),
        "was_fallback": bool(response.get("was_fallback")),
        "citations": response.get("citations", []),
        "provider": response.get("provider", "local"),
    }


_PROVIDER_BADGES = {
    "gemini": ("Gemini", "badge--mode-gemini"),
    "groq": ("Groq", "badge--mode-groq"),
    "openai": ("OpenAI", "badge--mode-openai"),
}


def _provider_badge(provider: str) -> str:
    label, css_class = _PROVIDER_BADGES.get(
        provider,
        ("Local · Rule-based", "badge--mode-local"),
    )
    return badge_html(label, css_class)


def _render_answer(item: dict[str, Any]) -> None:
    mode_badge = _provider_badge(item.get("provider", "local"))

    with st.container(border=True):
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;'
            f'gap:var(--sp-4)"><div><div class="kicker">Your question</div>'
            f'<div style="color:var(--text-on-dark);font-weight:600;margin-top:4px">'
            f'{escape(item["question"])}</div></div>{mode_badge}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p style="color:var(--text-on-dark);line-height:1.7;margin-top:var(--sp-4)">'
            f'{escape(item["answer"])}</p>',
            unsafe_allow_html=True,
        )

        if item["was_fallback"]:
            fallback_notice()
            return

        groups = _group_citations(item["citations"])
        if not groups:
            st.caption("No citations returned for this answer.")
            return

        st.markdown(
            f'<div class="kicker" style="margin-top:var(--sp-4)">Sources '
            f'<span class="badge badge--mode-openai">{len(groups)}</span></div>',
            unsafe_allow_html=True,
        )
        for index, group in enumerate(groups):
            page = group.get("page_number")
            header = f"{group['filename']}" + (f" · p.{page}" if page else "")
            with st.expander(header, expanded=(index == 0)):
                for snippet in group["snippets"][:2]:
                    st.markdown(
                        f'<p style="color:var(--text-faint);margin:0 0 var(--sp-2)">'
                        f"“{escape(snippet)}”</p>",
                        unsafe_allow_html=True,
                    )
                if isinstance(group.get("best"), (int, float)):
                    st.caption(_score_label(group["best"]))


def render() -> None:
    page_header("Ask", "Ask anything. Every answer is grounded in your uploaded documents.")

    with st.form("ask-form", clear_on_submit=False):
        question = st.text_area(
            "Question",
            placeholder="How does the matchmaking service work?",
            label_visibility="collapsed",
            height=88,
        )
        submitted = st.form_submit_button("Ask  →", type="primary")

    with st.expander("Try a demo question"):
        sample_cols = st.columns(2)
        for index, sample in enumerate(SAMPLE_QUESTIONS):
            if sample_cols[index % 2].button(
                sample, key=f"sample-{index}", use_container_width=True
            ):
                _run_query(sample)

    if submitted:
        _run_query(question)

    if st.session_state.get("last_error"):
        st.error(st.session_state["last_error"])
    elif st.session_state.get("last_answer"):
        _render_answer(st.session_state["last_answer"])

    page_footer("ask")
