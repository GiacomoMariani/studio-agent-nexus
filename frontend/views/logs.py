"""Log Storage page — wired to the real per-question log (question, answer, cost).

Logs are written automatically when a question is asked on the Ask page; they are never
posted directly. This page reads, searches, exports, and clears them.
"""

import csv
import io
from html import escape

import api
import streamlit as st
from components import badge_html, page_footer, page_header, placeholder, stat_card_html, toast

_CSV_FIELDS = [
    "created_at", "question", "answer", "model_name", "input_tokens",
    "output_tokens", "estimated_cost_usd", "citation_count", "was_fallback", "latency_ms",
]


def _summary(logs: list[dict]) -> dict:
    stored = len(logs)
    tokens = sum(
        int(log.get("input_tokens") or 0) + int(log.get("output_tokens") or 0)
        for log in logs
    )
    fallbacks = sum(1 for log in logs if log.get("was_fallback"))
    return {
        "stored": stored,
        "tokens": tokens,
        "avg_tokens": (round(tokens / stored) if stored else 0),
        # Positive framing: share of answers handled without falling back to rule-based.
        "success_rate": (round(100 * (stored - fallbacks) / stored) if stored else 100),
    }


def _mode_badge(model_name: str) -> str:
    name = model_name or ""
    if not name or name == "rule-based":
        return badge_html("Local · rule-based", "badge--mode-local")
    if name.startswith("gemini"):
        return badge_html(f"Gemini · {name}", "badge--mode-gemini")
    if name.startswith("gpt"):
        return badge_html(f"OpenAI · {name}", "badge--mode-openai")
    if name.startswith("llama") or name.startswith("groq"):
        return badge_html(f"Groq · {name}", "badge--mode-groq")
    return badge_html(f"LLM · {name}", "badge--mode-openai")


def _ts(created_at: str) -> str:
    return created_at[:19].replace("T", " ")


def _to_csv(logs: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for log in logs:
        writer.writerow({field: log.get(field, "") for field in _CSV_FIELDS})
    return buffer.getvalue()


def _render_entry(log: dict) -> None:
    tokens = int(log.get("input_tokens") or 0) + int(log.get("output_tokens") or 0)
    label = f"{_ts(log.get('created_at', ''))}  ·  {log.get('question', '')}  —  {tokens:,} tokens"
    with st.expander(label):
        st.markdown(_mode_badge(log.get("model_name", "")), unsafe_allow_html=True)
        flag = (
            ' <span class="badge badge--status-failed">fallback</span>'
            if log.get("was_fallback")
            else ""
        )
        st.markdown(
            f'<div class="kicker" style="margin-top:var(--sp-3)">Answer{flag}</div>'
            f'<p style="color:var(--text-on-dark)">{escape(log.get("answer", ""))}</p>',
            unsafe_allow_html=True,
        )
        meta = {
            "Prompt tokens": f"{int(log.get('input_tokens') or 0):,}",
            "Completion tokens": f"{int(log.get('output_tokens') or 0):,}",
            "Total tokens": f"{tokens:,}",
            "Citations": log.get("citation_count", 0),
            "Latency": f"{round(float(log.get('latency_ms') or 0))}ms",
            "Log id": log.get("query_id", ""),
        }
        cells = "".join(
            f'<div><div class="kicker">{escape(k)}</div>'
            f'<div style="color:var(--text-on-dark);font-weight:600">{escape(str(v))}</div></div>'
            for k, v in meta.items()
        )
        st.markdown(
            f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:var(--sp-4);'
            f'margin-top:var(--sp-3)">{cells}</div>',
            unsafe_allow_html=True,
        )


def render() -> None:
    page_header(
        "Log Storage",
        "Every question, the answer returned, and the tokens it consumed — persisted for "
        "audit and usage control.",
    )

    try:
        logs = api.list_query_logs(limit=100)
    except api.ApiError as exc:
        st.error(str(exc))
        page_footer("logs")
        return

    summary = _summary(logs)
    cols = st.columns(4)
    cards = [
        stat_card_html("Stored queries", str(summary["stored"]), "white", "most recent 100"),
        stat_card_html("Total tokens", f"{summary['tokens']:,}", "amber", "logged usage"),
        stat_card_html(
            "Avg tokens / query", f"{summary['avg_tokens']:,}", "white", "tokens per answer"
        ),
        stat_card_html(
            "AI success rate", f"{summary['success_rate']}%", "green",
            "answered without fallback",
        ),
    ]
    for col, card in zip(cols, cards, strict=False):
        col.markdown(card, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:var(--sp-6)'></div>", unsafe_allow_html=True)

    if not logs:
        placeholder("There are no logs. Ask a question on the Ask page to populate them.")
        page_footer("logs")
        return

    # Toolbar: search + export + clear
    search = st.text_input(
        "Search",
        placeholder="Search questions and answers…",
        label_visibility="collapsed",
    )
    needle = search.strip().lower()
    filtered = [
        log for log in logs
        if not needle
        or needle in log.get("question", "").lower()
        or needle in log.get("answer", "").lower()
    ]

    bar = st.columns([3, 1, 1])
    bar[0].caption(f"Showing {len(filtered)} of {len(logs)} recent")
    bar[1].download_button(
        "Export CSV",
        data=_to_csv(filtered),
        file_name="query_logs.csv",
        mime="text/csv",
        use_container_width=True,
    )
    if not st.session_state.get("logs_clear_confirm"):
        if bar[2].button("Clear logs", type="secondary", use_container_width=True):
            st.session_state["logs_clear_confirm"] = True
            st.rerun()
    else:
        if bar[2].button("Confirm clear", type="primary", use_container_width=True):
            try:
                api.clear_query_logs()
            except api.ApiError as exc:
                st.error(str(exc))
            else:
                st.session_state["logs_clear_confirm"] = False
                toast("Logs cleared")
                st.rerun()

    if not filtered:
        st.caption(f'No logs match "{search}".')

    for log in filtered:
        _render_entry(log)

    page_footer("logs")
