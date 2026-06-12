"""Studio Agent Nexus — Streamlit shell.

Custom dark sidebar + manual page routing (no Streamlit native multipage nav), the
design-system CSS, and dispatch to the per-page views in ``frontend/views/``.

Manual smoke test:
    streamlit run frontend/app.py
  - Sidebar shows wordmark, 5 nav items, provider indicator, role selector, credit.
  - Clicking a nav item switches the page and highlights it (amber).
  - Each page shows its header, a placeholder, and the "How it works" footer.
"""

import os
import sys

import streamlit as st

# Ensure local modules (components, styles, views) are importable when run via Streamlit.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from styles import CUSTOM_CSS  # noqa: E402
from views import ask, board, logs, risks, upload  # noqa: E402

st.set_page_config(
    page_title="Studio Agent Nexus",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Navigation registry
# ---------------------------------------------------------------------------
NAV = [
    ("upload", "Upload", ":material/upload:", upload),
    ("ask", "Ask", ":material/forum:", ask),
    ("board", "Board", ":material/view_kanban:", board),
    ("risks", "Risks", ":material/warning:", risks),
    ("logs", "Logs", ":material/database:", logs),
]
VIEW_BY_ID = {nav_id: view for nav_id, _, _, view in NAV}

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
st.session_state.setdefault("page", "ask")        # current nav page
st.session_state.setdefault("role", "Project Manager")  # role selector
st.session_state.setdefault("documents", None)    # real doc list
st.session_state.setdefault("last_answer", None)  # last Q&A result
st.session_state.setdefault("last_error", None)   # last Q&A error message, if any


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            """
            <div class="wordmark__row">
                <div class="wordmark__mark">
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none"
                         stroke="#0F172A" stroke-width="2.4" stroke-linecap="round"
                         stroke-linejoin="round">
                        <path d="M12 2 4 6v6c0 5 3.5 8 8 10 4.5-2 8-5 8-10V6z"/>
                        <path d="M9 12l2 2 4-4"/>
                    </svg>
                </div>
                <div class="wordmark__title">Studio Agent <span class="nexus">Nexus</span></div>
            </div>
            <div class="wordmark__sub">Production Intelligence</div>
            <div class="sidebar-divider"></div>
            """,
            unsafe_allow_html=True,
        )

        for nav_id, label, icon, _ in NAV:
            active = st.session_state["page"] == nav_id
            if st.button(
                label,
                key=f"nav_{nav_id}",
                icon=icon,
                type="primary" if active else "secondary",
                use_container_width=True,
            ):
                st.session_state["page"] = nav_id
                st.rerun()

        st.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)

        # Provider-agnostic indicator — the actual model varies by config (Gemini / Groq /
        # OpenAI / local) and is shown per-answer via the provider badge on the Ask page.
        st.markdown("<div class='sidebar-label'>AI engine</div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='color:var(--success);font-size:var(--fs-small);font-weight:600;"
            "margin-bottom:var(--sp-2)'>● Powered by AI</div>",
            unsafe_allow_html=True,
        )

        st.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)

        # Role selector
        st.markdown("<div class='sidebar-label'>Viewing as</div>", unsafe_allow_html=True)
        roles = ["Project Manager", "Team Member"]
        current_role = st.session_state["role"] if st.session_state["role"] in roles else roles[0]
        st.session_state["role"] = st.selectbox(
            "role",
            roles,
            index=roles.index(current_role),
            label_visibility="collapsed",
        )

        st.markdown(
            "<div class='sidebar-credit'>Built by Giacomo Mariani · "
            "<a href='https://github.com/GiacomoMariani/studio-agent-nexus' "
            "target='_blank' rel='noopener'>View source ↗</a></div>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
render_sidebar()
VIEW_BY_ID[st.session_state["page"]].render()
