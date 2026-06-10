from fastapi.testclient import TestClient

from main import app
from services.uploaded_text_store import SQLiteUploadedTextStore
from tests.units.test_pdf_parser import _single_page_pdf_bytes

client = TestClient(app)

AUTH_HEADERS = {"X-API-Key": "test-secret-key"}


class RecordingIngestionQueue:
    def __init__(self) -> None:
        self.text_upload_calls = []
        self.stored_text_upload_calls = []
        self.document_reindex_calls = []

    def enqueue_text_upload(self, worker, payload) -> None:
        self.text_upload_calls.append(
            {
                "worker": worker,
                "job_id": payload.job_id,
                "filename": payload.filename,
                "text": payload.text,
            }
        )

    def enqueue_stored_text_upload(self, worker, text_store, payload) -> None:
        self.stored_text_upload_calls.append(
            {
                "worker": worker,
                "text_store": text_store,
                "job_id": payload.job_id,
                "filename": payload.filename,
                "content_id": payload.content_id,
            }
        )

    def enqueue_document_reindex(self, worker, payload) -> None:
        self.document_reindex_calls.append(
            {
                "worker": worker,
                "job_id": payload.job_id,
                "document_id": payload.document_id,
            }
        )

def test_upload_document_requires_api_key():
    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "guide.txt",
                b"FastAPI is the backend framework.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing API key."
    }


def test_upload_document_returns_queued_ingestion_job():
    response = client.post(
        "/documents/upload",
        headers=AUTH_HEADERS,
        files={
            "file": (
                "guide.txt",
                b"FastAPI is the backend framework. Testing is important.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["job_id"].startswith("job-")
    assert payload["filename"] == "guide.txt"
    assert payload["status"] == "queued"
    assert payload["document_id"] is None
    assert payload["chunk_count"] is None
    assert payload["error_message"] is None
    assert payload["created_at"]
    assert payload["updated_at"]


def test_upload_document_uses_ingestion_queue_dependency(tmp_path):
    import main

    queue = RecordingIngestionQueue()
    text_store = SQLiteUploadedTextStore(tmp_path / "uploaded_texts.db")

    main.app.dependency_overrides[main.get_document_ingestion_queue] = lambda: queue
    main.app.dependency_overrides[main.get_uploaded_text_store] = lambda: text_store

    try:
        response = client.post(
            "/documents/upload",
            headers=AUTH_HEADERS,
            files={
                "file": (
                    "guide.txt",
                    b"FastAPI is the backend framework.",
                    "text/plain",
                )
            },
        )
    finally:
        main.app.dependency_overrides.pop(main.get_document_ingestion_queue, None)
        main.app.dependency_overrides.pop(main.get_uploaded_text_store, None)

    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "queued"

    assert len(queue.text_upload_calls) == 0
    assert len(queue.stored_text_upload_calls) == 1

    call = queue.stored_text_upload_calls[0]

    assert call["job_id"] == payload["job_id"]
    assert call["filename"] == "guide.txt"
    assert call["content_id"]
    assert call["text_store"].get_text(call["content_id"]) == (
        "FastAPI is the backend framework."
    )
    assert hasattr(call["worker"], "process_existing_text_upload_job_safely")


def test_upload_document_job_can_be_fetched_after_background_completion():
    upload_response = client.post(
        "/documents/upload",
        headers=AUTH_HEADERS,
        files={
            "file": (
                "guide.txt",
                b"FastAPI is the backend framework. Testing is important.",
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 200

    upload_payload = upload_response.json()
    job_id = upload_payload["job_id"]

    job_response = client.get(
        f"/documents/jobs/{job_id}",
        headers=AUTH_HEADERS,
    )

    assert job_response.status_code == 200

    job_payload = job_response.json()
    assert job_payload["job_id"] == job_id
    assert job_payload["filename"] == "guide.txt"
    assert job_payload["status"] == "completed"
    assert job_payload["document_id"].startswith("doc-")
    assert job_payload["chunk_count"] >= 1
    assert job_payload["error_message"] is None

def test_upload_document_accepts_markdown_files(tmp_path):
    import main

    queue = RecordingIngestionQueue()
    text_store = SQLiteUploadedTextStore(tmp_path / "uploaded_texts.db")

    main.app.dependency_overrides[main.get_document_ingestion_queue] = lambda: queue
    main.app.dependency_overrides[main.get_uploaded_text_store] = lambda: text_store

    try:
        response = client.post(
            "/documents/upload",
            headers=AUTH_HEADERS,
            files={
                "file": (
                    "guide.md",
                    b"# Handbook\n\nRemote work is allowed.",
                    "text/markdown",
                )
            },
        )
    finally:
        main.app.dependency_overrides.pop(main.get_document_ingestion_queue, None)
        main.app.dependency_overrides.pop(main.get_uploaded_text_store, None)

    assert response.status_code == 200

    assert len(queue.stored_text_upload_calls) == 1

    call = queue.stored_text_upload_calls[0]

    assert call["filename"] == "guide.md"
    assert call["text_store"].get_text(call["content_id"]) == (
        "# Handbook\n\nRemote work is allowed."
    )

def test_upload_document_accepts_pdf_files(tmp_path):
    import main

    queue = RecordingIngestionQueue()
    text_store = SQLiteUploadedTextStore(tmp_path / "uploaded_texts.db")

    main.app.dependency_overrides[main.get_document_ingestion_queue] = lambda: queue
    main.app.dependency_overrides[main.get_uploaded_text_store] = lambda: text_store

    try:
        response = client.post(
            "/documents/upload",
            headers=AUTH_HEADERS,
            files={
                "file": (
                    "remote-work.pdf",
                    _single_page_pdf_bytes(),
                    "application/pdf",
                )
            },
        )
    finally:
        main.app.dependency_overrides.pop(main.get_document_ingestion_queue, None)
        main.app.dependency_overrides.pop(main.get_uploaded_text_store, None)

    assert response.status_code == 200

    assert len(queue.stored_text_upload_calls) == 1

    call = queue.stored_text_upload_calls[0]
    stored_text = call["text_store"].get_text(call["content_id"])

    assert call["filename"] == "remote-work.pdf"
    assert "[Page 1]" in stored_text
    assert "Remote work is allowed." in stored_text

def test_upload_document_rejects_unsupported_files():
    response = client.post(
        "/documents/upload",
        headers=AUTH_HEADERS,
        files={
            "file": (
                "guide.docx",
                b"not supported yet",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Only .txt, .md, and .pdf files are supported."
    }


def test_upload_document_rejects_invalid_pdf():
    response = client.post(
        "/documents/upload",
        headers=AUTH_HEADERS,
        files={
            "file": (
                "guide.pdf",
                b"not really a pdf",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Uploaded file could not be read as a PDF."
    }


def test_upload_document_rejects_empty_text_file():
    response = client.post(
        "/documents/upload",
        headers=AUTH_HEADERS,
        files={
            "file": (
                "empty.txt",
                b"   ",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Uploaded document is empty."
    }


def test_get_document_ingestion_job_requires_api_key():
    response = client.get("/documents/jobs/job-missing")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing API key."
    }


def test_get_document_ingestion_job_returns_job_status():
    import main

    job = main.sqlite_ingestion_job_store.create_job("guide.txt")
    main.sqlite_ingestion_job_store.mark_completed(
        job_id=job.job_id,
        document_id="doc-123",
        chunk_count=3,
    )

    response = client.get(
        f"/documents/jobs/{job.job_id}",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["job_id"] == job.job_id
    assert payload["filename"] == "guide.txt"
    assert payload["status"] == "completed"
    assert payload["document_id"] == "doc-123"
    assert payload["chunk_count"] == 3
    assert payload["error_message"] is None
    assert payload["created_at"]
    assert payload["updated_at"]


def test_get_document_ingestion_job_returns_404_for_unknown_job():
    response = client.get(
        "/documents/jobs/job-missing",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Ingestion job not found."
    }


def test_ask_document_returns_grounded_answer_with_citations():
    upload_response = client.post(
        "/documents/upload",
        headers=AUTH_HEADERS,
        files={
            "file": (
                "guide.txt",
                (
                    b"FastAPI is the backend framework used in this project. "
                    b"Pytest is used for testing. "
                    b"Docker has not been added yet."
                ),
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 200

    job_id = upload_response.json()["job_id"]

    job_response = client.get(
        f"/documents/jobs/{job_id}",
        headers=AUTH_HEADERS,
    )

    assert job_response.status_code == 200

    document_id = job_response.json()["document_id"]
    assert document_id is not None

    response = client.post(
        "/documents/ask",
        headers=AUTH_HEADERS,
        json={
            "document_id": document_id,
            "question": "What is used for the backend?",
            "top_k": 2,
        },
    )

    assert response.status_code == 200

    payload = response.json()
    assert "FastAPI" in payload["answer"]
    assert len(payload["citations"]) >= 1

    first_citation = payload["citations"][0]

    assert first_citation["chunk_id"].startswith(f"{document_id}-chunk-")
    assert first_citation["filename"] == "guide.txt"
    assert first_citation["snippet"]
    assert first_citation["page_number"] is None
    assert 0.0 <= first_citation["vector_score"] <= 1.0
    assert 0.0 <= first_citation["keyword_score"] <= 1.0
    assert 0.0 <= first_citation["hybrid_score"] <= 1.0

def test_ask_documents_without_document_id_searches_all_documents():
    first_upload_response = client.post(
        "/documents/upload",
        headers=AUTH_HEADERS,
        files={
            "file": (
                "backend-guide.txt",
                b"FastAPI is the backend framework used in this project.",
                "text/plain",
            )
        },
    )

    second_upload_response = client.post(
        "/documents/upload",
        headers=AUTH_HEADERS,
        files={
            "file": (
                "testing-guide.txt",
                b"Pytest is used for automated testing in this project.",
                "text/plain",
            )
        },
    )

    assert first_upload_response.status_code == 200
    assert second_upload_response.status_code == 200

    response = client.post(
        "/documents/ask",
        headers=AUTH_HEADERS,
        json={
            "question": "What framework is used for the backend?",
            "top_k": 2,
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert "FastAPI" in payload["answer"]
    assert payload["was_fallback"] is False
    assert payload["provider"] == "local"
    assert len(payload["citations"]) >= 1
    assert payload["citations"][0]["filename"] == "backend-guide.txt"

def test_ask_document_returns_404_for_unknown_document():
    response = client.post(
        "/documents/ask",
        headers=AUTH_HEADERS,
        json={
            "document_id": "doc-missing",
            "question": "What is used for the backend?",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Document not found."
    }

def test_ask_pdf_document_returns_page_number_in_citation():
    upload_response = client.post(
        "/documents/upload",
        headers=AUTH_HEADERS,
        files={
            "file": (
                "remote-work.pdf",
                _single_page_pdf_bytes(),
                "application/pdf",
            )
        },
    )

    assert upload_response.status_code == 200

    job_id = upload_response.json()["job_id"]

    job_response = client.get(
        f"/documents/jobs/{job_id}",
        headers=AUTH_HEADERS,
    )

    assert job_response.status_code == 200

    document_id = job_response.json()["document_id"]
    assert document_id is not None

    response = client.post(
        "/documents/ask",
        headers=AUTH_HEADERS,
        json={
            "document_id": document_id,
            "question": "Is remote work allowed?",
            "top_k": 1,
        },
    )

    assert response.status_code == 200

    payload = response.json()
    assert len(payload["citations"]) >= 1

    first_citation = payload["citations"][0]

    assert first_citation["filename"] == "remote-work.pdf"
    assert first_citation["page_number"] == 1
    assert "Remote work is allowed." in first_citation["snippet"]

def test_list_documents_requires_api_key():
    response = client.get("/documents")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing API key."
    }

def test_list_documents_returns_uploaded_documents():
    upload_response = client.post(
        "/documents/upload",
        headers=AUTH_HEADERS,
        files={
            "file": (
                "guide.txt",
                b"FastAPI is the backend framework. Testing is important.",
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 200

    job_id = upload_response.json()["job_id"]

    job_response = client.get(
        f"/documents/jobs/{job_id}",
        headers=AUTH_HEADERS,
    )

    assert job_response.status_code == 200

    document_id = job_response.json()["document_id"]
    assert document_id is not None

    response = client.get("/documents", headers=AUTH_HEADERS)

    assert response.status_code == 200

    payload = response.json()

    assert len(payload["documents"]) == 1

    document = payload["documents"][0]

    assert document["document_id"] == document_id
    assert document["filename"] == "guide.txt"
    assert document["file_type"] == "txt"
    assert document["upload_date"]
    assert document["status"] == "indexed"
    assert document["page_count"] is None
    assert document["chunk_count"] == job_response.json()["chunk_count"]

def test_delete_document_requires_api_key():
    response = client.delete("/documents/doc-missing")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing API key."
    }


def test_delete_document_returns_404_for_unknown_document():
    response = client.delete(
        "/documents/doc-missing",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Document not found."
    }


def test_delete_document_removes_uploaded_document():
    upload_response = client.post(
        "/documents/upload",
        headers=AUTH_HEADERS,
        files={
            "file": (
                "guide.txt",
                b"FastAPI is the backend framework. Testing is important.",
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 200

    job_id = upload_response.json()["job_id"]

    job_response = client.get(
        f"/documents/jobs/{job_id}",
        headers=AUTH_HEADERS,
    )

    assert job_response.status_code == 200

    document_id = job_response.json()["document_id"]
    assert document_id is not None

    delete_response = client.delete(
        f"/documents/{document_id}",
        headers=AUTH_HEADERS,
    )

    assert delete_response.status_code == 200
    assert delete_response.json() == {
        "document_id": document_id,
        "deleted": True,
    }

    list_response = client.get("/documents", headers=AUTH_HEADERS)

    assert list_response.status_code == 200
    assert list_response.json() == {
        "documents": []
    }

def test_reindex_document_requires_api_key():
    response = client.post("/documents/doc-missing/reindex")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing API key."
    }


def test_reindex_document_returns_404_for_unknown_document():
    response = client.post(
        "/documents/doc-missing/reindex",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Document not found."
    }


def test_reindex_document_enqueues_reindex_job(tmp_path):
    import main

    queue = RecordingIngestionQueue()
    text_store = SQLiteUploadedTextStore(tmp_path / "uploaded_texts.db")

    main.app.dependency_overrides[main.get_document_ingestion_queue] = lambda: queue
    main.app.dependency_overrides[main.get_uploaded_text_store] = lambda: text_store

    try:
        upload_response = client.post(
            "/documents/upload",
            headers=AUTH_HEADERS,
            files={
                "file": (
                    "guide.txt",
                    b"FastAPI is the backend framework. Testing is important.",
                    "text/plain",
                )
            },
        )

        assert upload_response.status_code == 200

        original_upload_call = queue.stored_text_upload_calls[0]
        document = main.sqlite_document_store.save_document(
            filename=original_upload_call["filename"],
            text=original_upload_call["text_store"].get_text(
                original_upload_call["content_id"]
            ),
            chunk_payloads=[
                {
                    "text": "FastAPI is the backend framework.",
                    "embedding": [1.0, 0.0],
                    "page_number": None,
                }
            ],
        )

        response = client.post(
            f"/documents/{document.document_id}/reindex",
            headers=AUTH_HEADERS,
        )
    finally:
        main.app.dependency_overrides.pop(main.get_document_ingestion_queue, None)
        main.app.dependency_overrides.pop(main.get_uploaded_text_store, None)

    assert response.status_code == 200

    payload = response.json()

    assert payload["document_id"] == document.document_id
    assert payload["filename"] == "guide.txt"
    assert payload["status"] == "queued"

    assert len(queue.document_reindex_calls) == 1
    assert queue.document_reindex_calls[0]["document_id"] == document.document_id
    assert queue.document_reindex_calls[0]["job_id"] == payload["job_id"]

def test_list_document_query_logs_requires_api_key():
    response = client.get("/admin/document-query-logs")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing API key."
    }


def test_list_document_query_logs_returns_recent_document_questions():
    upload_response = client.post(
        "/documents/upload",
        headers=AUTH_HEADERS,
        files={
            "file": (
                "guide.txt",
                b"FastAPI is the backend framework. Testing is important.",
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 200

    job_id = upload_response.json()["job_id"]

    job_response = client.get(
        f"/documents/jobs/{job_id}",
        headers=AUTH_HEADERS,
    )

    assert job_response.status_code == 200

    document_id = job_response.json()["document_id"]
    assert document_id is not None

    ask_response = client.post(
        "/documents/ask",
        headers=AUTH_HEADERS,
        json={
            "document_id": document_id,
            "question": "What is used for the backend?",
            "top_k": 1,
        },
    )

    assert ask_response.status_code == 200

    response = client.get(
        "/admin/document-query-logs",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200

    payload = response.json()
    assert len(payload["logs"]) == 1

    log = payload["logs"][0]

    assert log["query_id"].startswith("query-")
    assert log["document_id"] == document_id
    assert log["question"] == "What is used for the backend?"
    assert "FastAPI" in log["answer"]
    assert log["citation_count"] >= 1
    assert log["latency_ms"] >= 0
    assert log["was_fallback"] is False
    assert log["created_at"]
    assert len(log["retrieved_sources"]) >= 1

    source = log["retrieved_sources"][0]

    assert source["source_id"].startswith("source-")
    assert source["query_id"] == log["query_id"]
    assert source["chunk_id"].startswith(f"{document_id}-chunk-")
    assert source["filename"] == "guide.txt"
    assert source["snippet"]
    assert source["page_number"] is None
    assert 0.0 <= source["vector_score"] <= 1.0
    assert 0.0 <= source["keyword_score"] <= 1.0
    assert 0.0 <= source["hybrid_score"] <= 1.0

def test_list_knowledge_gaps_returns_fallback_document_questions():
    import main

    main.sqlite_document_query_log_store.record_query(
        document_id="doc-1",
        question="What backend framework is used?",
        answer="FastAPI is used.",
        citation_count=1,
        was_fallback=False,
        latency_ms=5.0,
        retrieved_sources=[],
    )

    main.sqlite_document_query_log_store.record_query(
        document_id="doc-2",
        question="What is the refund policy?",
        answer="I could not find the answer in the provided context.",
        citation_count=0,
        was_fallback=True,
        latency_ms=7.0,
        retrieved_sources=[],
    )

    response = client.get(
        "/admin/knowledge-gaps",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200

    payload = response.json()

    assert len(payload["gaps"]) == 1

    gap = payload["gaps"][0]

    assert gap["query_id"].startswith("query-")
    assert gap["document_id"] == "doc-2"
    assert gap["question"] == "What is the refund policy?"
    assert gap["answer"] == "I could not find the answer in the provided context."
    assert gap["citation_count"] == 0
    assert gap["latency_ms"] == 7.0
    assert gap["created_at"]

def test_list_knowledge_gaps_requires_api_key():
    response = client.get("/admin/knowledge-gaps")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing API key."
    }