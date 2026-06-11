"""Risks & Contradictions page — findings read from the DB (posted via the risks API).

"Scan for risks" is a demo gesture that reveals the findings stored in the database.
"""

from html import escape

import api
import streamlit as st
from components import badge_html, page_footer, page_header, placeholder

SEVERITIES = ["Critical", "High", "Medium", "Low"]
_SEV_CLASS = {
    "Critical": "badge--critical",
    "High": "badge--high",
    "Medium": "badge--medium",
    "Low": "badge--low",
}
_SEV_COLOR = {
    "Critical": "var(--pri-critical)",
    "High": "var(--pri-high)",
    "Medium": "var(--pri-medium)",
    "Low": "var(--pri-low)",
}
ALL_DOCS = "All documents"


def _sev_badge(severity: str) -> str:
    return badge_html(severity, _SEV_CLASS.get(severity, "badge--medium"))


def _in_scope(finding: dict, selected: str) -> bool:
    if selected == ALL_DOCS:
        return True
    if finding.get("kind") == "contradiction":
        return selected in (finding.get("a_file"), finding.get("b_file"))
    return finding.get("source") == selected


def _risk_card(finding: dict) -> None:
    color = _SEV_COLOR.get(finding.get("severity", ""), "var(--pri-medium)")
    st.markdown(
        f'<div class="card" style="border-left:4px solid {color};margin-bottom:var(--sp-4)">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<div style="display:flex;gap:var(--sp-3);align-items:center">'
        f'<span style="color:{color}">⚠</span>{_sev_badge(finding.get("severity", ""))}</div>'
        f'<span class="kicker" style="color:var(--text-muted-on-light)">Risk</span></div>'
        f'<div style="font-weight:600;color:var(--text-on-light);margin-top:var(--sp-3)">'
        f'{escape(finding.get("title", ""))}</div>'
        f'<div style="color:var(--text-faint);font-size:0.9rem;margin-top:4px">'
        f'{escape(finding.get("description", ""))}</div>'
        f'<div style="font-style:italic;color:var(--text-muted-on-light);'
        f'font-size:var(--fs-caption);margin-top:var(--sp-3)">'
        f'Source: {escape(finding.get("source", ""))}</div></div>',
        unsafe_allow_html=True,
    )


def _panel(file: str, text: str) -> str:
    return (
        '<div style="background:var(--surface-muted);border-radius:8px;padding:var(--sp-4)">'
        f'<div style="font-weight:600;color:var(--text-on-light);font-size:var(--fs-small)">'
        f'{escape(file)}</div>'
        f'<div style="color:var(--text-muted-on-light);font-style:italic;margin-top:4px">'
        f'“{escape(text)}”</div></div>'
    )


def _contradiction_card(finding: dict) -> None:
    vs = '<div style="align-self:center;color:var(--text-muted-on-dark);font-weight:700">VS</div>'
    st.markdown(
        f'<div class="card" style="border-left:4px solid var(--error);margin-bottom:var(--sp-4)">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<div style="display:flex;gap:var(--sp-3);align-items:center">'
        f'<span style="color:var(--error)">⚡</span>'
        f'{_sev_badge(finding.get("severity", ""))}</div>'
        f'<span class="kicker" style="color:var(--text-muted-on-light)">Contradiction</span></div>'
        f'<div style="font-weight:600;color:var(--text-on-light);margin:var(--sp-3) 0 var(--sp-4)">'
        f'{escape(finding.get("title", ""))}</div>'
        f'<div style="display:grid;grid-template-columns:1fr auto 1fr;gap:var(--sp-3)">'
        f'{_panel(finding.get("a_file", ""), finding.get("a_text", ""))}'
        f'{vs}'
        f'{_panel(finding.get("b_file", ""), finding.get("b_text", ""))}</div></div>',
        unsafe_allow_html=True,
    )


def render() -> None:
    page_header(
        "Risks & Contradictions",
        "Detect risks, gaps, and conflicts across your documents.",
    )

    scanned = st.session_state.get("risks_scanned", False)
    if st.button(
        "Re-scan" if scanned else "Scan for risks →",
        type="secondary" if scanned else "primary",
    ):
        try:
            with st.spinner("Scanning documents for risks and contradictions…"):
                api.scan_risks()
        except api.ApiError as exc:
            st.error(str(exc))
        else:
            st.session_state["risks_scanned"] = True
            st.rerun()

    if not scanned:
        placeholder("Scan your documents to surface risks, gaps, and contradictions.")
        page_footer("risks")
        return

    try:
        findings = api.list_risks()
        documents = api.list_documents()
    except api.ApiError as exc:
        st.error(str(exc))
        page_footer("risks")
        return

    if not findings:
        placeholder("No risks or contradictions found. Post findings to populate this page.")
        page_footer("risks")
        return

    # Filters
    doc_names = sorted({d.get("filename", "") for d in documents if d.get("filename")})
    selected = st.selectbox("Source document", [ALL_DOCS, *doc_names])
    kind = st.radio(
        "Type", ["All", "Risks", "Contradictions"], horizontal=True, label_visibility="collapsed"
    )
    sev_filter = st.multiselect("Severity", SEVERITIES, placeholder="All severities")

    scoped = [f for f in findings if _in_scope(f, selected)]

    def _matches(finding: dict) -> bool:
        if kind == "Risks" and finding.get("kind") != "risk":
            return False
        if kind == "Contradictions" and finding.get("kind") != "contradiction":
            return False
        if sev_filter and finding.get("severity") not in sev_filter:
            return False
        return True

    filtered = [f for f in scoped if _matches(f)]

    risks_n = sum(1 for f in scoped if f.get("kind") == "risk")
    contra_n = sum(1 for f in scoped if f.get("kind") == "contradiction")
    crit_n = sum(1 for f in scoped if f.get("severity") == "Critical")
    st.markdown(
        f'<div class="stats-line" style="margin:var(--sp-4) 0">{risks_n} risks · '
        f"{contra_n} contradictions · {crit_n} critical</div>",
        unsafe_allow_html=True,
    )

    if not filtered:
        st.caption("No findings match these filters.")

    for finding in filtered:
        if finding.get("kind") == "contradiction":
            _contradiction_card(finding)
        else:
            _risk_card(finding)

    page_footer("risks")
