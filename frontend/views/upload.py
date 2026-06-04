"""Upload / Knowledge Base page — wired to the real ingestion backend."""

import time

import api
import streamlit as st
from components import badge_html, page_footer, page_header, placeholder, toast

_STATUS_CLASS = {
    "indexed": "badge--status-indexed",
    "completed": "badge--status-indexed",
    "processing": "badge--status-processing",
    "queued": "badge--status-processing",
    "failed": "badge--status-failed",
}
_TYPE_CLASS = {"md": "badge--type-md", "pdf": "badge--type-pdf"}
_TERMINAL_JOB_STATES = {"completed", "failed"}


def _status_badge(status: str) -> str:
    label = status.capitalize()
    cls = _STATUS_CLASS.get(status.lower(), "badge--mode-local")
    return badge_html(label, cls)


def _type_badge(file_type: str) -> str:
    cls = _TYPE_CLASS.get(file_type.lower(), "badge--mode-local")
    return badge_html(file_type.upper(), cls)


def _poll_job(job_id: str, label: str) -> str:
    """Poll a job to a terminal state; return the final status ('completed'/'failed')."""
    with st.spinner(label):
        for _ in range(60):
            try:
                job = api.get_job(job_id)
            except api.ApiError:
                return "failed"
            status = str(job.get("status", "")).lower()
            if status in _TERMINAL_JOB_STATES:
                return status
            time.sleep(1)
    return "processing"  # timed out; treat as still-processing


def _render_library() -> None:
    try:
        docs = api.list_documents()
    except api.ApiError as exc:
        st.error(str(exc))
        placeholder("No documents to show. Start the backend, then reload this page.")
        return

    total_chunks = sum(int(d.get("chunk_count") or 0) for d in docs)
    st.markdown(
        f'<div class="stats-line" style="margin-bottom:var(--sp-4)">'
        f"{len(docs)} documents · {total_chunks} chunks</div>",
        unsafe_allow_html=True,
    )

    if not docs:
        placeholder(
            "No documents yet. On first start the backend embeds the demo documents — "
            "give it a moment and reload."
        )
        return

    for doc in docs:
        document_id = doc.get("document_id", "")
        is_demo = bool(doc.get("is_demo"))
        cols = st.columns([0.9, 4.0, 1.4, 1.2, 2.0], vertical_alignment="center")

        cols[0].markdown(_type_badge(doc.get("file_type", "")), unsafe_allow_html=True)

        lock = "🔒 " if is_demo else ""
        demo_tag = (
            ' <span class="muted-caption">Demo</span>' if is_demo else ""
        )
        cols[1].markdown(
            f'<span style="color:var(--text-on-dark)">{lock}{doc.get("filename", "")}</span>'
            f"{demo_tag}",
            unsafe_allow_html=True,
        )

        cols[2].markdown(_status_badge(doc.get("status", "")), unsafe_allow_html=True)
        cols[3].markdown(
            f'<span class="muted-caption">{doc.get("chunk_count", 0)} chunks</span>',
            unsafe_allow_html=True,
        )

        if is_demo:
            cols[4].markdown(
                '<span class="muted-caption">—</span>', unsafe_allow_html=True
            )
        else:
            action_cols = cols[4].columns(2)
            if action_cols[0].button(
                "Re-index", key=f"reindex-{document_id}", use_container_width=True
            ):
                _handle_reindex(document_id)
            if action_cols[1].button(
                "Delete", key=f"delete-{document_id}", use_container_width=True
            ):
                _handle_delete(document_id)


def _handle_reindex(document_id: str) -> None:
    try:
        job = api.reindex_document(document_id)
    except api.ApiError as exc:
        st.error(str(exc))
        return
    final = _poll_job(job.get("job_id", ""), "Re-indexing…")
    if final == "failed":
        st.error("Re-index failed.")
    else:
        toast("Document re-indexed")
        st.rerun()


def _handle_delete(document_id: str) -> None:
    try:
        api.delete_document(document_id)
    except api.ApiError as exc:
        st.error(str(exc))
        return
    toast("Document deleted")
    st.rerun()


def _render_upload_panel() -> None:
    st.markdown(
        '<h2 style="font-size:var(--fs-h2);font-weight:600;color:var(--text-on-dark);'
        'margin:0 0 var(--sp-4)">Add a document</h2>',
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader(
        "Drop .md or .pdf here",
        type=["md", "pdf"],
        label_visibility="collapsed",
    )
    st.caption("Markdown · PDF")

    if st.button("Upload and index →", type="primary", use_container_width=True):
        if uploaded is None:
            st.warning("Choose a .md or .pdf file first.")
            return
        try:
            job = api.upload_document(uploaded.name, uploaded.getvalue(), uploaded.type)
        except api.ApiError as exc:
            st.error(str(exc))
            return
        final = _poll_job(job.get("job_id", ""), "Indexing…")
        if final == "failed":
            st.error("Indexing failed. Check the file and try again.")
        else:
            toast(f"Indexed {uploaded.name}")
            st.rerun()

    st.markdown(
        '<p class="muted-caption" style="margin-top:var(--sp-3)">'
        "Demo documents are seeded automatically and cannot be deleted.</p>",
        unsafe_allow_html=True,
    )


def render() -> None:
    page_header(
        "Knowledge Base",
        "Upload and manage the documents Studio Agent Nexus reasons over.",
    )

    library_col, upload_col = st.columns([0.65, 0.35], gap="large")
    with library_col:
        _render_library()
    with upload_col:
        _render_upload_panel()

    page_footer("upload")
