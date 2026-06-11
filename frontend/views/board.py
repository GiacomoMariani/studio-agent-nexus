"""Board page — displays persisted reviews + planning suggestions from the DB.

Data is posted to the backend by an external producer; this page is a read-only,
role-aware view. No GitHub anywhere.
"""

from html import escape

import api
import streamlit as st
from components import (
    badge_html,
    dept_badge_html,
    page_footer,
    page_header,
    placeholder,
    priority_badge_html,
    toast,
)
from fixtures import BOARD_STATES, REVIEW_STATES, VIEW_STATES

PRIORITY_RANK = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
STATE_LABEL = {s["id"]: s["label"] for s in BOARD_STATES}
STATE_COLOR = {s["id"]: s["color"] for s in BOARD_STATES}
ALL_DOCS = "All documents"


def _sort_items(items: list[dict]) -> list[dict]:
    """Priority (Critical→Low), then most-recently-updated first."""
    by_recency = sorted(items, key=lambda r: r.get("updated_at", ""), reverse=True)
    return sorted(by_recency, key=lambda r: PRIORITY_RANK.get(r.get("priority"), 99))


def _state_pill(state: str) -> str:
    label = STATE_LABEL.get(state, state)
    color = STATE_COLOR.get(state, "#64748B")
    return (
        f'<span class="badge" style="background:transparent;border:1px solid {color};'
        f'color:{color}">● {escape(label)}</span>'
    )


def _badges_html(item: dict, with_state: bool = True) -> str:
    parts = [
        dept_badge_html(item.get("department", "")),
        priority_badge_html(item.get("priority", "")),
    ]
    if with_state and item.get("state"):
        parts.append(_state_pill(item["state"]))
    chips = "".join(parts)
    return (
        '<div style="display:flex;gap:var(--sp-2);align-items:center;flex-wrap:wrap">'
        f"{chips}</div>"
    )


def _review_card(item: dict, with_state: bool = True) -> None:
    dept = escape(item.get("department", "").lower())
    st.markdown(
        f'<div class="card" style="border-left:4px solid var(--dept-{dept});'
        f'margin-bottom:var(--sp-3)">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;gap:var(--sp-3)">'
        f'{_badges_html(item, with_state)}'
        f'<span class="muted-caption">{escape(item.get("source", ""))}</span></div>'
        f'<div style="font-weight:600;color:var(--text-on-light);margin-top:var(--sp-3)">'
        f'{escape(item.get("title", ""))}</div>'
        f'<div style="color:var(--text-faint);font-size:0.9rem;margin-top:4px">'
        f'{escape(item.get("description", ""))}</div></div>',
        unsafe_allow_html=True,
    )


def _suggestion_card(item: dict, can_export: bool) -> None:
    with st.container(border=True):
        st.markdown(
            f'{_badges_html(item, with_state=False)}'
            f'<div style="font-weight:600;color:var(--text-on-dark);margin-top:var(--sp-3)">'
            f'{escape(item.get("title", ""))}</div>'
            f'<div style="color:var(--text-muted-on-dark);font-style:italic;font-size:0.875rem;'
            f'margin-top:4px">Why: {escape(item.get("reason", ""))}</div>',
            unsafe_allow_html=True,
        )
        if can_export:
            if st.button("Export to backlog →", key=f"promote-{item['suggestion_id']}"):
                try:
                    api.promote_suggestion(item["suggestion_id"])
                except api.ApiError as exc:
                    st.error(str(exc))
                    return
                toast("Promoted to backlog")
                st.rerun()
        else:
            st.caption("Switch to Project Manager to export to backlog.")


# --- Draft Jira tasks (ticket-017): board-top generator, ephemeral preview ---------------

JIRA_STUB_MESSAGE = "Missing Project Manager pass — Jira sync not configured"
_ISSUE_BADGE_CLASS = {
    "Story": "badge--issue-story",
    "Task": "badge--issue-task",
    "Bug": "badge--issue-bug",
    "Epic": "badge--issue-epic",
}


def _issue_badge(issue_type: str) -> str:
    return badge_html(issue_type, _ISSUE_BADGE_CLASS.get(issue_type, "badge--issue-task"))


def _resolve_scope_document_id(selected: str, documents: list[dict]) -> str | None:
    """Map the panel's document selection to a document_id (None ⇒ all documents)."""
    if selected == ALL_DOCS:
        return None
    for document in documents:
        if document.get("filename") == selected:
            return document.get("document_id")
    return None


def _jira_draft_card(draft: dict) -> None:
    labels = "".join(
        badge_html(str(label), "badge--mode-local") for label in draft.get("labels", [])
    )
    criteria = "".join(
        f"<li>{escape(str(c))}</li>" for c in draft.get("acceptance_criteria", [])
    )
    points = draft.get("story_points")
    points_html = (
        f'<span class="muted-caption">{escape(str(points))} pts</span>' if points else ""
    )
    labels_html = (
        '<div style="display:flex;gap:var(--sp-2);flex-wrap:wrap;margin-top:var(--sp-3)">'
        f"{labels}</div>"
        if labels
        else ""
    )
    criteria_html = (
        '<div class="muted-caption" style="margin-top:var(--sp-3)">Acceptance criteria</div>'
        f'<ul style="margin:4px 0 0 1.1rem;color:var(--text-muted-on-dark);'
        f'font-size:0.85rem">{criteria}</ul>'
        if criteria
        else ""
    )
    with st.container(border=True):
        st.markdown(
            '<div style="display:flex;gap:var(--sp-2);align-items:center;flex-wrap:wrap">'
            f'{_issue_badge(draft.get("issue_type", ""))}'
            f'{priority_badge_html(draft.get("priority", ""))}'
            f'{dept_badge_html(draft.get("department", ""))}{points_html}</div>'
            f'<div style="font-weight:600;color:var(--text-on-dark);margin-top:var(--sp-3)">'
            f'{escape(draft.get("summary", ""))}</div>'
            f'<div style="color:var(--text-muted-on-dark);font-size:0.875rem;margin-top:4px">'
            f'{escape(draft.get("description", ""))}</div>'
            f"{labels_html}{criteria_html}"
            f'<div class="muted-caption" style="margin-top:var(--sp-3)">'
            f'Source: {escape(draft.get("source", ""))}</div>',
            unsafe_allow_html=True,
        )
        if st.button("Confirm on Jira", key=f"jira-confirm-{draft.get('draft_id', '')}"):
            # Deliberate stub: no Jira connection, no persistence, shown to every role.
            st.warning(JIRA_STUB_MESSAGE)


def _jira_task_panel(documents: list[dict]) -> None:
    st.markdown(
        '<div class="kicker" style="color:var(--accent)">✦ Draft Jira tasks</div>'
        '<h2 style="margin:4px 0 var(--sp-3)">Generate task drafts from your documents</h2>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Generate Jira-shaped task drafts and review them before they'd go to Jira. "
        "Drafts are not saved."
    )

    doc_names = sorted({d.get("filename", "") for d in documents if d.get("filename")})
    selected = st.selectbox("Generate from", [ALL_DOCS, *doc_names], key="jira_gen_scope")

    left, right = st.columns([1, 1])
    with left:
        if st.button("Generate tasks →", type="primary", key="jira_generate"):
            document_id = _resolve_scope_document_id(selected, documents)
            try:
                with st.spinner("Generating Jira task drafts…"):
                    st.session_state["jira_task_drafts"] = api.generate_jira_tasks(document_id)
            except api.ApiError as exc:
                st.error(str(exc))
            else:
                st.rerun()
    with right:
        if st.session_state.get("jira_task_drafts") is not None:
            if st.button("Clear drafts", key="jira_clear"):
                st.session_state.pop("jira_task_drafts", None)
                st.rerun()

    drafts = st.session_state.get("jira_task_drafts")
    if drafts is None:
        return
    if not drafts:
        st.caption("No tasks generated for this selection.")
        return

    st.markdown(
        f'<div class="stats-line" style="margin:var(--sp-3) 0">'
        f"{len(drafts)} draft task(s) · not saved</div>",
        unsafe_allow_html=True,
    )
    for draft in drafts:
        _jira_draft_card(draft)


def render() -> None:
    page_header(
        "Board",
        "Review what's ready and promote the work you're still missing — scoped to a "
        "source document.",
    )

    try:
        documents = api.list_documents()
        reviews = api.list_reviews()
        suggestions = api.list_suggestions()
    except api.ApiError as exc:
        st.error(str(exc))
        page_footer("board")
        return

    # Draft Jira tasks (ticket-017) — board-top generator; ephemeral, persists nothing.
    _jira_task_panel(documents)
    st.divider()

    # Source-document scope (Q3)
    doc_names = sorted({d.get("filename", "") for d in documents if d.get("filename")})
    selected = st.selectbox("Source document", [ALL_DOCS, *doc_names])

    def in_scope(item: dict) -> bool:
        return selected == ALL_DOCS or item.get("source") == selected

    reviews = [r for r in reviews if in_scope(r)]
    suggestions = [s for s in suggestions if in_scope(s)]

    if not reviews and not suggestions:
        placeholder("There are no tasks.")
        page_footer("board")
        return

    can_export = st.session_state.get("role") == "Project Manager"

    # Zone 1 — Ready for review (ai + lead)
    review_zone = _sort_items([r for r in reviews if r.get("state") in REVIEW_STATES])
    st.markdown(
        f'<div class="kicker" style="color:var(--accent);margin-top:var(--sp-6)">'
        f'★ Top priority</div>'
        f'<h2 style="margin:4px 0 var(--sp-4)">Ready for review '
        f'<span class="muted-caption">{len(review_zone)}</span></h2>',
        unsafe_allow_html=True,
    )
    if review_zone:
        for item in review_zone:
            _review_card(item)
    else:
        st.caption("Nothing is waiting for review.")

    # Zone 2 — Planning add-on
    st.markdown(
        '<h2 style="margin:var(--sp-8) 0 var(--sp-4)">Tasks you may still need</h2>',
        unsafe_allow_html=True,
    )
    if suggestions:
        for item in suggestions:
            _suggestion_card(item, can_export)
    else:
        st.caption("No planning suggestions.")

    # Zone 3 — State viewer
    st.markdown('<h2 style="margin:var(--sp-8) 0 var(--sp-4)">Showing</h2>', unsafe_allow_html=True)
    view_state = st.selectbox(
        "State",
        VIEW_STATES,
        format_func=lambda s: STATE_LABEL.get(s, s),
        label_visibility="collapsed",
    )
    view_items = _sort_items([r for r in reviews if r.get("state") == view_state])
    if view_items:
        for item in view_items:
            _review_card(item, with_state=False)
    else:
        st.caption(f"Nothing in {STATE_LABEL.get(view_state, view_state)}.")

    page_footer("board")
