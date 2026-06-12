"""Ask page — grounded Q&A wired to the real document backend."""

import os
from html import escape
from typing import Any

import api
import streamlit as st
from components import (
    JIRA_STUB_MESSAGE,
    badge_html,
    dept_badge_html,
    fallback_notice,
    issue_type_badge,
    page_footer,
    page_header,
    priority_badge_html,
)
from fixtures import SAMPLE_QUESTIONS

TOP_K = 5
DEFAULT_SNIPPETS_SHOWN = 3


def _snippets_shown() -> int:
    """Max snippets rendered per source group (SOURCE_SNIPPETS_SHOWN in .env, default 3)."""
    raw = os.getenv("SOURCE_SNIPPETS_SHOWN", "")
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_SNIPPETS_SHOWN
    return value if value >= 1 else DEFAULT_SNIPPETS_SHOWN


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
                "document_id": cite.get("document_id"),
                "page_number": cite.get("page_number"),
                "best": None,
                "snips": [],
                "source_ids": [],
                "passages": [],
            },
        )
        source_id = cite.get("source_id")
        if isinstance(source_id, int) and source_id not in group["source_ids"]:
            group["source_ids"].append(source_id)
        if snippet and snippet not in [s for _, s in group["snips"]]:
            group["snips"].append((score if score is not None else -1.0, snippet))
            group["passages"].append(
                {
                    "source_id": source_id,
                    "snippet": snippet,
                    "page_number": cite.get("page_number"),
                    "vector_score": cite.get("vector_score"),
                    "keyword_score": cite.get("keyword_score"),
                    "hybrid_score": cite.get("hybrid_score"),
                    "_sort": score if score is not None else -1.0,
                }
            )
        if score is not None and (group["best"] is None or score > group["best"]):
            group["best"] = score
            group["page_number"] = cite.get("page_number")

    result = []
    for group in groups.values():
        group["snips"].sort(key=lambda pair: pair[0], reverse=True)
        group["snippets"] = [s for _, s in group["snips"]]
        group["passages"].sort(key=lambda passage: passage["_sort"], reverse=True)
        group["source_ids"].sort()
        result.append(group)
    result.sort(key=lambda g: (g["best"] is not None, g["best"] or 0.0), reverse=True)
    return result


def _score_breakdown(passage: dict[str, Any]) -> str:
    # Per-type retrieval scores, relative within this result set (min-max normalised).
    def _pct(value: object) -> str:
        return f"{value * 100:.0f}%" if isinstance(value, (int, float)) else "—"

    source_id = passage.get("source_id")
    label = f"[{source_id}] " if isinstance(source_id, int) else ""
    return (
        f"{label}vector {_pct(passage.get('vector_score'))} · "
        f"keyword {_pct(passage.get('keyword_score'))} · "
        f"hybrid {_pct(passage.get('hybrid_score'))}"
    )


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
        "input_tokens": response.get("input_tokens", 0),
        "output_tokens": response.get("output_tokens", 0),
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


@st.cache_data(show_spinner=False)
def _source_content(document_id: str) -> dict[str, Any] | None:
    """Fetch a source document's stored text once per session (cached by id)."""
    try:
        return api.get_document_content(document_id)
    except api.ApiError:
        return None


def _render_source_download(group: dict[str, Any]) -> None:
    document_id = group.get("document_id")
    if not document_id:
        return
    content = _source_content(document_id)
    if not content:
        return
    filename = content.get("filename", "source.txt")
    # A PDF's stored content is its extracted text, not the original binary — name it .txt.
    download_name = f"{filename}.txt" if filename.lower().endswith(".pdf") else filename
    # Right-aligned so it reads as a header action at the top of the source panel.
    _, right = st.columns([3, 1])
    with right:
        st.download_button(
            "⬇  Download source",
            data=content.get("content", ""),
            file_name=download_name,
            mime="text/plain",
            key=f"dl-{document_id}",
            use_container_width=True,
        )


def _should_offer_tasks(item: dict[str, Any]) -> bool:
    """Offer task actions only when an LLM actually answered (not the rule fallback)."""
    return item.get("provider", "local") != "local" and not item.get("was_fallback")


def _render_related_task(task: dict[str, Any]) -> None:
    score = task.get("score")
    match = f" · match {score * 100:.0f}%" if isinstance(score, (int, float)) else ""
    st.markdown(
        '<div class="card" style="margin-bottom:var(--sp-2)">'
        '<div style="display:flex;gap:var(--sp-2);align-items:center;flex-wrap:wrap">'
        f'{dept_badge_html(task.get("department", ""))}'
        f'{priority_badge_html(task.get("priority", ""))}'
        f'<span style="font-weight:600;color:var(--text-on-light)">'
        f'{escape(task.get("title", ""))}</span></div>'
        f'<div class="muted-caption" style="margin-top:4px">{escape(task.get("kind", ""))}'
        f"{match}</div></div>",
        unsafe_allow_html=True,
    )


def _suggested_task_card(draft: dict[str, Any]) -> None:
    with st.container(border=True):
        st.markdown(
            '<div style="display:flex;gap:var(--sp-2);align-items:center;flex-wrap:wrap">'
            f'{issue_type_badge(draft.get("issue_type", ""))}'
            f'{priority_badge_html(draft.get("priority", ""))}'
            f'{dept_badge_html(draft.get("department", ""))}</div>'
            f'<div style="font-weight:600;color:var(--text-on-dark);margin-top:var(--sp-2)">'
            f'{escape(draft.get("summary", ""))}</div>'
            f'<div style="color:var(--text-muted-on-dark);font-size:0.875rem;margin-top:4px">'
            f'{escape(draft.get("description", ""))}</div>',
            unsafe_allow_html=True,
        )
        if st.button("Confirm on Jira", key=f"ask-jira-{draft.get('draft_id', '')}"):
            # Deliberate stub — no Jira connection, no persistence (ticket-017/018).
            st.warning(JIRA_STUB_MESSAGE)


def _render_task_suggestions(item: dict[str, Any]) -> None:
    """LLM-gated: a button that pulls related existing tasks + suggested new drafts."""
    if not _should_offer_tasks(item):
        return

    question = item.get("question", "")
    state = st.session_state.get("ask_task_suggestions")
    have_results = bool(state) and state.get("question") == question

    if st.button(
        "Find related & suggested tasks",
        key="find-tasks",
        type="primary",
        icon=":material/auto_awesome:",
    ):
        try:
            with st.spinner("Finding related and suggested tasks…"):
                result = api.ask_task_suggestions(question, item.get("answer", ""))
        except api.ApiError as exc:
            st.error(str(exc))
            return
        st.session_state["ask_task_suggestions"] = {"question": question, **result}
        st.rerun()

    if not have_results:
        return

    related = state.get("related", [])
    suggested = state.get("suggested", [])

    if related:
        st.markdown(
            '<div class="kicker" style="margin-top:var(--sp-4)">Related tasks</div>',
            unsafe_allow_html=True,
        )
        for task in related:
            _render_related_task(task)

    if suggested:
        st.markdown(
            '<div class="kicker" style="margin-top:var(--sp-4)">Suggested new tasks</div>',
            unsafe_allow_html=True,
        )
        st.caption("Drafts — not saved.")
        for draft in suggested:
            _suggested_task_card(draft)

    if not related and not suggested:
        st.caption("No related or suggested tasks for this question.")


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

        total_tokens = item.get("input_tokens", 0) + item.get("output_tokens", 0)
        if total_tokens:
            st.caption(
                f"≈ {total_tokens:,} tokens "
                f"({item.get('input_tokens', 0):,} in · {item.get('output_tokens', 0):,} out)"
            )

        if item["was_fallback"]:
            fallback_notice()
            return

        _render_task_suggestions(item)

        groups = _group_citations(item["citations"])
        if not groups:
            st.caption("No citations returned for this answer.")
            return

        st.markdown(
            f'<div class="kicker" style="margin-top:var(--sp-4)">Sources '
            f'<span class="badge badge--mode-openai">{len(item["citations"])}</span></div>',
            unsafe_allow_html=True,
        )
        snippet_limit = _snippets_shown()
        for index, group in enumerate(groups):
            marker = "".join(f"[{sid}] " for sid in group.get("source_ids") or [])
            header = f"{marker}{group['filename']}"
            with st.expander(header, expanded=(index == 0)):
                _render_source_download(group)
                for passage in group["passages"][:snippet_limit]:
                    page = passage.get("page_number")
                    page_label = f"  ·  p.{page}" if page else ""
                    st.markdown(
                        f'<p style="color:var(--text-faint);margin:0 0 2px">'
                        f"“{escape(passage['snippet'])}”</p>",
                        unsafe_allow_html=True,
                    )
                    st.caption(_score_breakdown(passage) + page_label)
                if len(group["passages"]) > snippet_limit:
                    st.markdown(
                        '<p style="color:var(--text-faint);margin:0">…</p>',
                        unsafe_allow_html=True,
                    )


def _pick_pending_question(
    running: bool,
    submitted: bool,
    typed_question: str,
    sample_clicked: str | None,
) -> str | None:
    """Choose the question to run, or None.

    Returns None while a query is already running so a second submission can never
    start until the first finishes. Otherwise a typed submission wins over a demo click.
    """
    if running:
        return None
    if submitted and typed_question.strip():
        return typed_question.strip()
    if sample_clicked is not None and sample_clicked.strip():
        return sample_clicked.strip()
    return None


def render() -> None:
    page_header("Ask", "Ask anything. Every answer is grounded in your uploaded documents.")

    running = st.session_state.get("query_running", False)

    with st.form("ask-form", clear_on_submit=False):
        question = st.text_area(
            "Question",
            placeholder="How does the matchmaking service work?",
            label_visibility="collapsed",
            height=88,
        )
        submitted = st.form_submit_button("Ask  →", type="primary", disabled=running)

    # Answer (and the in-flight spinner) render here — right under the ask box, above the demos.
    answer_slot = st.container()

    with st.expander("Try a demo question", expanded=True):
        sample_cols = st.columns(2)
        sample_clicked: str | None = None
        for index, sample in enumerate(SAMPLE_QUESTIONS):
            if sample_cols[index % 2].button(
                sample,
                key=f"sample-{index}",
                use_container_width=True,
                disabled=running,
            ):
                sample_clicked = sample

    pending = _pick_pending_question(running, submitted, question, sample_clicked)

    if pending is not None:
        # Lock submissions and run on the next rerun, where every button is disabled.
        st.session_state["pending_question"] = pending
        st.session_state["query_running"] = True
        st.rerun()
    elif submitted and not question.strip():
        with answer_slot:
            st.warning("Enter a question before asking.")

    with answer_slot:
        if running and st.session_state.get("pending_question"):
            queued = st.session_state.pop("pending_question")
            try:
                _run_query(queued)
            finally:
                st.session_state["query_running"] = False
            st.rerun()

        if st.session_state.get("last_error"):
            st.error(st.session_state["last_error"])
        elif st.session_state.get("last_answer"):
            _render_answer(st.session_state["last_answer"])

    page_footer("ask")
