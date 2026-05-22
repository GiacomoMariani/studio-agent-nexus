import os
from html import escape
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("APP_API_KEY", "")
HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}

SAMPLE_QUESTIONS = [
    "What are the standard support hours?",
    "How long does standard demo order delivery take?",
    "How long does refund review take?",
    "Which orders are packed and awaiting carrier pickup?",
    "How many delivered orders are marked as paid?",
    "Who owns the order for Paper Trail Books?",
    "Which package includes monthly reporting and knowledge-gap review?",
    "Which package includes evaluation mode and retrieval debugging?",
    "How many remote work days are allowed each week?",
    "Who approves expenses above EUR 500?",
    "Who should review API sync or webhook issues?",
    "What are the main steps in the chatbot workflow?",
]

# ---------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------

st.set_page_config(
    page_title="Business RAG Chatbot",
    page_icon="💬",
    layout="wide",
)

CUSTOM_CSS = """
<style>
    .block-container {
        padding-top: 1.6rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    .top-header {
        margin-bottom: 1.1rem;
    }

    .top-header h1 {
        font-size: 2.35rem;
        line-height: 1.1;
        margin-bottom: 0.4rem;
    }

    .top-header p {
        color: #64748b;
        font-size: 1rem;
        max-width: 850px;
    }

    .skill-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.9rem;
        margin-bottom: 0.4rem;
    }

    .skill-chip {
        border: 1px solid #cbd5e1;
        background: #f8fafc;
        color: #334155;
        padding: 0.35rem 0.65rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 600;
    }

    .chat-focus {
        padding: 1.25rem;
        border: 1px solid #bfdbfe;
        border-radius: 1.1rem;
        background: #eff6ff;
        color: #0f172a;
        margin-bottom: 1rem;
    }

    .chat-focus strong {
        color: #0f172a;
    }

    .section-card {
        padding: 1rem 1.1rem;
        border: 1px solid #e5e7eb;
        border-radius: 1rem;
        background: #ffffff;
        height: 100%;
    }

    .section-card h3 {
        margin-top: 0;
        margin-bottom: 0.35rem;
        font-size: 1.05rem;
    }

    .section-card p {
        color: #475569;
        font-size: 0.92rem;
        margin-bottom: 0;
    }

    .step-card {
        padding: 1rem;
        border-radius: 0.9rem;
        border: 1px solid #e5e7eb;
        background: #f8fafc;
        margin-bottom: 0.75rem;
    }

    .step-number {
        display: inline-block;
        width: 1.7rem;
        height: 1.7rem;
        line-height: 1.7rem;
        border-radius: 999px;
        text-align: center;
        background: #0f172a;
        color: white;
        font-size: 0.8rem;
        font-weight: 700;
        margin-right: 0.45rem;
    }

    .muted {
        color: #64748b;
    }

    .footer {
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #e5e7eb;
        color: #64748b;
        font-size: 0.9rem;
    }

    .sample-question-selected {
        padding: 0.85rem 1rem;
        border: 1px solid #22c55e;
        border-radius: 0.55rem;
        background: rgba(34, 197, 94, 0.14);
        text-align: center;
        font-weight: 700;
        margin-bottom: 0.75rem;
    }

    .sample-question-selected small {
        display: block;
        color: #22c55e;
        font-weight: 700;
        margin-top: 0.25rem;
    }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------

def api_request(
        method: str,
        path: str,
        *,
        timeout: int = 15,
        **kwargs: Any,
) -> dict[str, Any]:
    if not API_KEY:
        raise RuntimeError("Missing APP_API_KEY in .env")

    response = requests.request(
        method=method,
        url=f"{API_URL}{path}",
        headers=HEADERS,
        timeout=timeout,
        **kwargs,
    )

    if response.status_code == 401:
        raise RuntimeError("Unauthorized. Check APP_API_KEY in .env.")

    if response.status_code == 403:
        try:
            detail = response.json().get("detail", "Action not allowed.")
        except ValueError:
            detail = "Action not allowed."
        raise RuntimeError(detail)

    response.raise_for_status()

    if not response.content:
        return {}

    return response.json()


def get_docs() -> list[dict[str, Any]]:
    return api_request("GET", "/documents")["documents"]


def ask_docs(question: str) -> dict[str, Any]:
    return api_request(
        "POST",
        "/documents/ask",
        json={
            "question": question,
            "top_k": 5,
        },
        timeout=30,
    )


def upload_doc(uploaded_file) -> dict[str, Any]:
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type or "application/octet-stream",
        )
    }

    return api_request(
        "POST",
        "/documents/upload",
        files=files,
        timeout=60,
    )


def reindex_doc(doc_id: str) -> dict[str, Any]:
    return api_request(
        "POST",
        f"/documents/{doc_id}/reindex",
        timeout=15,
    )


def delete_doc(doc_id: str) -> dict[str, Any]:
    return api_request(
        "DELETE",
        f"/documents/{doc_id}",
        timeout=15,
    )


def get_logs(limit: int = 10) -> list[dict[str, Any]]:
    return api_request(
        "GET",
        "/admin/document-query-logs",
        params={"limit": limit},
        timeout=15,
    )["logs"]


# ---------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------

if "chat" not in st.session_state:
    st.session_state["chat"] = []

if "latest_answer" not in st.session_state:
    st.session_state["latest_answer"] = None

if "pending_question" not in st.session_state:
    st.session_state["pending_question"] = None

if "pending_sample_question" not in st.session_state:
    st.session_state["pending_sample_question"] = None

if "latest_error" not in st.session_state:
    st.session_state["latest_error"] = None


def load_documents() -> list[dict[str, Any]]:
    if "docs" not in st.session_state:
        st.session_state["docs"] = get_docs()

    return st.session_state["docs"]


def load_query_logs() -> list[dict[str, Any]]:
    if "logs" not in st.session_state:
        st.session_state["logs"] = get_logs()

    return st.session_state["logs"]


def queue_question(question: str, *, sample_question: bool = False) -> None:
    cleaned_question = question.strip()

    if not cleaned_question:
        st.warning("Enter a question before asking the chatbot.")
        return

    st.session_state["pending_question"] = cleaned_question
    st.session_state["pending_sample_question"] = (
        cleaned_question if sample_question else None
    )
    st.session_state["latest_error"] = None
    st.rerun()


def submit_question(question: str) -> bool:
    cleaned_question = question.strip()

    if not cleaned_question:
        st.warning("Enter a question before asking the chatbot.")
        return False

    try:
        result = ask_docs(cleaned_question)

        answer_item = {
            "question": cleaned_question,
            "answer": result.get("answer", ""),
            "was_fallback": result.get("was_fallback", False),
            "citations": result.get("citations", []),
        }

        st.session_state["latest_answer"] = answer_item
        st.session_state["latest_error"] = None
        st.session_state["chat"].append(answer_item)
        st.session_state.pop("logs", None)

        return True

    except (requests.RequestException, RuntimeError) as exc:
        st.session_state["latest_error"] = f"Could not get an answer: {exc}"
        return False


# ---------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------

def render_answer_mode_notice() -> None:
    answerer_type = os.getenv("DOCUMENT_ANSWERER_TYPE", "rule").strip().lower()
    model_client_type = os.getenv("DOCUMENT_QA_MODEL_CLIENT_TYPE", "fake").strip().lower()
    model_name = os.getenv("DOCUMENT_QA_MODEL_NAME", "not configured").strip()

    if answerer_type == "llm" and model_client_type == "openai":
        st.info(f"OpenAI-backed answers are enabled using `{model_name}`.")
    elif answerer_type == "llm":
        st.info(
            "LLM answers are enabled for local testing. "
            "Contact the person who gave you this link to try the OpenAI-backed demo."
        )
    else:
        st.info(
            "OpenAI-backed answers are implemented but currently disabled. "
            "Contact the person who gave you this link to try them."
        )


def render_feature_card(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="section-card">
            <h3>{title}</h3>
            <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_workflow_step(number: int, title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="step-card">
            <div>
                <span class="step-number">{number}</span>
                <strong>{title}</strong>
            </div>
            <div class="muted" style="margin-top: 0.45rem;">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def group_citations_by_source(
        citations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, Any], dict[str, Any]] = {}

    for citation in citations:
        filename = citation.get("filename", "Unknown source")
        page_number = citation.get("page_number")
        key = (filename, page_number)
        snippet = citation.get("snippet", "No snippet available.")
        score = citation.get("hybrid_score")

        if key not in grouped:
            grouped[key] = {
                "filename": filename,
                "page_number": page_number,
                "snippets": [],
                "hybrid_score": score if isinstance(score, (int, float)) else None,
            }

        if snippet not in grouped[key]["snippets"]:
            grouped[key]["snippets"].append(snippet)

        current_score = grouped[key].get("hybrid_score")
        if isinstance(score, (int, float)) and (
                current_score is None
                or score > current_score
        ):
            grouped[key]["hybrid_score"] = score

    return sorted(
        grouped.values(),
        key=lambda source: (
            source.get("hybrid_score") is not None,
            source.get("hybrid_score") or 0,
        ),
        reverse=True,
    )


def show_sources(citations: list[dict[str, Any]]) -> None:
    if not citations:
        st.caption("No citations returned for this answer.")
        return

    source_groups = group_citations_by_source(citations)

    if not source_groups:
        st.caption("No citations returned for this answer.")
        return

    best_score = source_groups[0].get("hybrid_score")

    if isinstance(best_score, (int, float)):
        score_cutoff = best_score * 0.90

        visible_sources = [
            source
            for source in source_groups
            if isinstance(source.get("hybrid_score"), (int, float))
            and source["hybrid_score"] >= score_cutoff
        ][:2]
    else:
        visible_sources = source_groups[:1]

    if not visible_sources:
        visible_sources = source_groups[:1]

    hidden_source_count = len(source_groups) - len(visible_sources)

    st.markdown("#### Grounding sources")

    for source in visible_sources:
        page = source.get("page_number")
        page_text = f", page {page}" if page else ""
        filename = source.get("filename", "Unknown source")
        title = f"{filename}{page_text}"
        snippets = source.get("snippets", [])

        with st.expander(title):
            if len(snippets) <= 1:
                st.write(snippets[0] if snippets else "No snippet available.")
            else:
                for index, snippet in enumerate(snippets[:3], start=1):
                    st.markdown(f"**Excerpt {index}**")
                    st.write(snippet)

                if len(snippets) > 3:
                    st.caption(
                        f"{len(snippets) - 3} additional retrieved excerpts hidden."
                    )

            score = source.get("hybrid_score")
            if isinstance(score, (int, float)):
                st.caption(f"Best retrieval score: {score:.3f}")

    if hidden_source_count > 0:
        st.caption(
            f"{hidden_source_count} lower-ranked source group hidden. "
            "Full retrieval details are available in the query logs."
        )


def render_latest_answer(answer_item: dict[str, Any]) -> None:
    with st.container(border=True):
        st.markdown("### Answer")
        st.markdown(f"**Question:** {answer_item['question']}")

        if answer_item["was_fallback"]:
            st.warning(answer_item["answer"])
        else:
            st.success("Answer found in the knowledge base.")
            st.write(answer_item["answer"])

        show_sources(answer_item["citations"])


def render_doc_rows(
        docs: list[dict[str, Any]],
        *,
        allow_delete: bool,
) -> None:
    if not docs:
        st.info("No documents in this layer yet.")
        return

    for doc in docs:
        filename = doc.get("filename", "Untitled document")
        status = doc.get("status", "unknown")
        chunk_count = doc.get("chunk_count", 0)
        page_count = doc.get("page_count")
        document_id = doc["document_id"]

        with st.container(border=True):
            info_col, action_col = st.columns([5, 2])

            with info_col:
                st.markdown(f"**{filename}**")
                st.caption("Indexed source available for retrieval and grounded answers.")

                metric_cols = st.columns(3)

                with metric_cols[0]:
                    st.metric("Status", status)

                with metric_cols[1]:
                    st.metric("Chunks", chunk_count)

                with metric_cols[2]:
                    st.metric("Pages", page_count if page_count else "—")

            with action_col:
                st.markdown("**Actions**")

                if st.button(
                        "Re-index",
                        key=f"reindex-{document_id}",
                        use_container_width=True,
                ):
                    try:
                        reindex_doc(document_id)
                        st.session_state.pop("docs", None)
                        st.success(f"Queued re-index for {filename}")
                        st.rerun()
                    except (requests.RequestException, RuntimeError) as exc:
                        st.error(f"Could not re-index document: {exc}")

                if allow_delete:
                    if st.button(
                            "Delete",
                            key=f"delete-{document_id}",
                            use_container_width=True,
                    ):
                        try:
                            delete_doc(document_id)
                            st.session_state.pop("docs", None)
                            st.success(f"Deleted {filename}")
                            st.rerun()
                        except (requests.RequestException, RuntimeError) as exc:
                            st.error(f"Could not delete document: {exc}")
                else:
                    st.caption("Protected demo document")


# ---------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------

st.markdown(
    """
    <div class="top-header">
        <h1>Business RAG Chatbot</h1>
        <p>
            Ask questions over business documents and get grounded answers with
            citations. This demo shows document ingestion, retrieval, source
            inspection, and chatbot UX for an AI-engineering portfolio project.
        </p>
        <div class="skill-row">
            <span class="skill-chip">RAG</span>
            <span class="skill-chip">Document parsing</span>
            <span class="skill-chip">Embeddings</span>
            <span class="skill-chip">Vector / hybrid search</span>
            <span class="skill-chip">LLM orchestration</span>
            <span class="skill-chip">Citations</span>
            <span class="skill-chip">Streamlit UI</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "Demo environment: this page is for testing only. "
    "Do not upload confidential, personal, financial, legal, or sensitive business data."
)

render_answer_mode_notice()

if not API_KEY:
    st.error("Missing APP_API_KEY in .env")
    st.stop()

# ---------------------------------------------------------------------
# Chat — primary focus
# ---------------------------------------------------------------------

st.markdown("## Ask the document chatbot")

st.markdown(
    """
    <div class="chat-focus">
        <strong>Start here:</strong> ask a question about the indexed documents.
        The chatbot retrieves relevant chunks and answers with citations when
        supporting evidence is found.
    </div>
    """,
    unsafe_allow_html=True,
)

is_answering = st.session_state["pending_question"] is not None

with st.form("chat-form", clear_on_submit=True):
    question = st.text_input(
        "Question",
        placeholder="Example: What are the standard support hours?",
        disabled=is_answering,
    )

    submitted = st.form_submit_button(
        "Ask the chatbot",
        type="primary",
        use_container_width=True,
        disabled=is_answering,
    )

if submitted:
    queue_question(question)

answer_placeholder = st.empty()

with st.expander("Try a demo question", expanded=is_answering):
    st.caption(
        "These prompts are useful for testing retrieval, citations, fallback behavior, "
        "and cross-document reasoning."
    )

    for index, sample_question in enumerate(SAMPLE_QUESTIONS, start=1):
        if sample_question == st.session_state["pending_sample_question"]:
            st.markdown(
                f"""
                <div class="sample-question-selected">
                    {escape(sample_question)}
                    <small>Answering…</small>
                </div>
                """,
                unsafe_allow_html=True,
            )
            continue

        if st.button(
                sample_question,
                key=f"sample-question-{index}",
                use_container_width=True,
                disabled=is_answering,
        ):
            queue_question(sample_question, sample_question=True)

with answer_placeholder.container():
    pending_question = st.session_state["pending_question"]

    if pending_question:
        with st.container(border=True):
            st.markdown("### Answer")
            st.markdown(f"**Question:** {pending_question}")
            st.info("Retrieving sources and generating an answer…")

            with st.spinner("Working on your answer..."):
                submit_question(pending_question)

        st.session_state["pending_question"] = None
        st.session_state["pending_sample_question"] = None
        st.rerun()

    elif st.session_state["latest_error"]:
        with st.container(border=True):
            st.markdown("### Answer")
            st.error(st.session_state["latest_error"])

    elif st.session_state["latest_answer"]:
        render_latest_answer(st.session_state["latest_answer"])

if len(st.session_state["chat"]) > 1:
    with st.expander("Previous conversation", expanded=False):
        if st.button("Clear conversation"):
            st.session_state["chat"] = []
            st.session_state["latest_answer"] = None
            st.rerun()

        for item in reversed(st.session_state["chat"][:-1]):
            st.markdown(f"**Question:** {item['question']}")

            if item["was_fallback"]:
                st.warning(item["answer"])
            else:
                st.write(item["answer"])

            show_sources(item["citations"])
            st.divider()

st.divider()

# ---------------------------------------------------------------------
# Documents — visible below chat, no tabs
# ---------------------------------------------------------------------

st.markdown("## Documents available to the chatbot")

st.caption(
    "The chatbot searches across two document layers: protected demo documents "
    "and temporary uploaded documents for local testing."
)

upload_col, stats_col = st.columns([1.15, 1], gap="large")

with upload_col:
    with st.container(border=True):
        st.markdown("### Upload a temporary test document")
        st.caption(
            "Supported formats: TXT, Markdown, and PDF. Uploaded documents can be "
            "indexed, queried, re-indexed, and deleted."
        )

        uploaded_file = st.file_uploader(
            "Choose a document",
            type=["txt", "md", "pdf"],
        )

        if st.button(
                "Upload and index document",
                type="primary",
                use_container_width=True,
        ):
            if uploaded_file is None:
                st.warning("Choose a document before uploading.")
            else:
                try:
                    upload_doc(uploaded_file)
                    st.session_state.pop("docs", None)
                    st.success("Temporary document uploaded successfully.")
                    st.rerun()
                except (requests.RequestException, RuntimeError) as exc:
                    st.error(f"Could not upload document: {exc}")

with stats_col:
    with st.container(border=True):
        st.markdown("### Document-analysis workflow")
        st.markdown(
            """
            Uploaded documents become part of the RAG pipeline:

            1. File ingestion  
            2. Parsing and chunking  
            3. Indexing for retrieval  
            4. Question answering with citations  
            5. Source inspection and logging  
            """
        )

refresh_col, _ = st.columns([1, 4])

with refresh_col:
    if st.button("Refresh documents", use_container_width=True):
        st.session_state.pop("docs", None)
        st.rerun()

try:
    docs = load_documents()

    demo_docs = [doc for doc in docs if doc.get("is_demo")]
    user_docs = [doc for doc in docs if not doc.get("is_demo")]

    total_chunks = sum(doc.get("chunk_count", 0) for doc in docs)

    metric_cols = st.columns(4)

    with metric_cols[0]:
        st.metric("Total documents", len(docs))

    with metric_cols[1]:
        st.metric("Demo documents", len(demo_docs))

    with metric_cols[2]:
        st.metric("User uploads", len(user_docs))

    with metric_cols[3]:
        st.metric("Indexed chunks", total_chunks)

    st.markdown("### Layer 1: Preloaded demo knowledge base")
    st.caption(
        "These fictional documents are bundled with the app, loaded automatically, "
        "and protected from deletion."
    )
    render_doc_rows(demo_docs, allow_delete=False)

    st.markdown("### Layer 2: Temporary uploaded documents")
    st.caption(
        "These documents are uploaded during testing and can be re-indexed or deleted."
    )
    render_doc_rows(user_docs, allow_delete=True)

except (requests.RequestException, RuntimeError) as exc:
    st.error(f"Could not load documents: {exc}")

st.divider()

# ---------------------------------------------------------------------
# Project explanation below documents
# ---------------------------------------------------------------------

st.markdown("## Project details")

overview_col, workflow_col = st.columns([1, 1.15], gap="large")

with overview_col:
    st.markdown("### What this project demonstrates")

    card_cols_1 = st.columns(2)

    with card_cols_1[0]:
        render_feature_card(
            "Production-style AI app",
            "A Streamlit interface connected to a secured backend API.",
        )

    with card_cols_1[1]:
        render_feature_card(
            "Document QA workflow",
            "Users can upload documents, index them, and ask natural-language questions.",
        )

    card_cols_2 = st.columns(2)

    with card_cols_2[0]:
        render_feature_card(
            "Grounded answers",
            "Responses include source snippets so users can inspect the evidence.",
        )

    with card_cols_2[1]:
        render_feature_card(
            "RAG observability",
            "Logs expose fallback behavior, latency, citation counts, and retrieval scores.",
        )

with workflow_col:
    st.markdown("### How the RAG chatbot works")

    render_workflow_step(
        1,
        "Ingest documents",
        "Demo files and temporary uploads are sent to the backend document pipeline.",
    )

    render_workflow_step(
        2,
        "Parse, chunk, and index",
        "Documents are converted into searchable chunks that can be re-indexed when needed.",
    )

    render_workflow_step(
        3,
        "Retrieve relevant context",
        "For each question, the app requests the most relevant document chunks.",
    )

    render_workflow_step(
        4,
        "Generate grounded answers",
        "The chatbot answers using retrieved context and returns citations for verification.",
    )

    render_workflow_step(
        5,
        "Monitor quality",
        "Query logs make retrieval quality, fallbacks, sources, and latency visible.",
    )

st.markdown("## Technical architecture")

architecture_cols = st.columns(3)

with architecture_cols[0]:
    render_feature_card(
        "Streamlit frontend",
        "A clean interface for upload, chat, source review, and RAG observability.",
    )

with architecture_cols[1]:
    render_feature_card(
        "Backend API integration",
        "The UI communicates with secured document and query endpoints using an API key.",
    )

with architecture_cols[2]:
    render_feature_card(
        "Document pipeline",
        "Documents are uploaded, parsed, chunked, indexed, and made available for retrieval.",
    )

architecture_cols_2 = st.columns(3)

with architecture_cols_2[0]:
    render_feature_card(
        "Retrieval layer",
        "Questions are matched against indexed chunks and ranked by relevance.",
    )

with architecture_cols_2[1]:
    render_feature_card(
        "LLM orchestration",
        "The backend returns grounded answers, fallback decisions, citations, and metadata.",
    )

with architecture_cols_2[2]:
    render_feature_card(
        "Quality monitoring",
        "Query logs expose latency, fallback status, citation count, and retrieved sources.",
    )

skills_col, use_cases_col = st.columns([1, 1], gap="large")

with skills_col:
    st.markdown("### Skills demonstrated")
    st.markdown(
        """
        - Retrieval-Augmented Generation
        - Document parsing and ingestion
        - Chunking and indexing workflows
        - Embedding-based or hybrid retrieval concepts
        - Source-grounded answer generation
        - Prompt and fallback behavior design
        - Streamlit app development
        - Chatbot UI and product UX
        - API integration and error handling
        - RAG evaluation and observability
        """
    )

with use_cases_col:
    st.markdown("### Example use cases")
    st.markdown(
        """
        - Internal policy assistant
        - Sales enablement knowledge base
        - Customer support document assistant
        - Invoice, order, or operations lookup
        - Employee onboarding chatbot
        - Contract or FAQ exploration tool
        - Lightweight analyst assistant for business documents
        """
    )

st.divider()

# ---------------------------------------------------------------------
# Admin query logs
# ---------------------------------------------------------------------

st.markdown("## Recent query logs")

st.caption(
    "Logs help evaluate answer quality, fallback behavior, retrieval sources, "
    "citation coverage, and latency."
)

refresh_logs_col, logs_hint_col = st.columns([1, 4])

with refresh_logs_col:
    if st.button("Refresh logs", use_container_width=True):
        st.session_state.pop("logs", None)
        st.rerun()

with logs_hint_col:
    st.caption(
        "Ask a few questions first, then refresh this section to inspect retrieval behavior."
    )

try:
    logs = load_query_logs()

    if not logs:
        st.info("No query logs yet.")
    else:
        answered_count = sum(1 for log in logs if not log.get("was_fallback"))
        fallback_count = sum(1 for log in logs if log.get("was_fallback"))

        log_metric_cols = st.columns(3)

        with log_metric_cols[0]:
            st.metric("Displayed logs", len(logs))

        with log_metric_cols[1]:
            st.metric("Answered", answered_count)

        with log_metric_cols[2]:
            st.metric("Fallbacks", fallback_count)

        for log in logs:
            was_fallback = log.get("was_fallback", False)
            status = "Fallback" if was_fallback else "Answered"
            question = log.get("question", "Untitled question")
            answer = log.get("answer", "")
            citation_count = log.get("citation_count", 0)
            latency = log.get("latency_ms")

            latency_text = (
                f"{latency:.2f} ms"
                if isinstance(latency, (int, float))
                else "Not available"
            )

            with st.expander(f"{status} — {question}"):
                st.write(f"**Answer:** {answer}")
                st.write(f"**Citations:** {citation_count}")
                st.write(f"**Latency:** {latency_text}")

                sources = log.get("retrieved_sources", [])

                if sources:
                    st.markdown("**Retrieved sources**")

                    for source in sources:
                        page = source.get("page_number")
                        page_text = f", page {page}" if page else ""
                        score = source.get("hybrid_score")
                        filename = source.get("filename", "Unknown source")

                        if isinstance(score, (int, float)):
                            st.write(
                                f"- {filename}{page_text} "
                                f"(score: {score:.3f})"
                            )
                        else:
                            st.write(f"- {filename}{page_text}")
                else:
                    st.caption("No retrieved sources were logged for this query.")

except (requests.RequestException, RuntimeError) as exc:
    st.error(f"Could not load query logs: {exc}")

# ---------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------

st.markdown(
    """
    <div class="footer">
        <strong>Business RAG Chatbot</strong> — a Streamlit portfolio demo for
        document ingestion, retrieval-augmented generation, grounded answers,
        citations, and RAG observability.
    </div>
    """,
    unsafe_allow_html=True,
)