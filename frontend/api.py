"""HTTP client for the Studio Agent Nexus backend.

The Streamlit frontend talks to the FastAPI backend over HTTP only (no service imports).
Environment is read at call time so values can be set in `.env` or overridden in tests.
"""

import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


class ApiError(Exception):
    """A user-facing backend error with a clean message."""


def _base_url() -> str:
    return os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")


def _api_key() -> str:
    return os.getenv("APP_API_KEY", "")


def _detail(response: requests.Response, default: str) -> str:
    try:
        return response.json().get("detail", default)
    except (ValueError, AttributeError):
        return default


def _request(method: str, path: str, *, timeout: int = 15, **kwargs: Any) -> Any:
    api_key = _api_key()
    if not api_key:
        raise ApiError("Missing APP_API_KEY — set it in your .env file.")

    url = f"{_base_url()}{path}"
    try:
        response = requests.request(
            method, url, headers={"X-API-Key": api_key}, timeout=timeout, **kwargs
        )
    except requests.RequestException as exc:
        raise ApiError(
            f"Could not reach the backend at {_base_url()}. Is it running?"
        ) from exc

    if response.status_code == 401:
        raise ApiError("Unauthorized — APP_API_KEY does not match the backend.")
    if response.status_code in (403, 404):
        raise ApiError(_detail(response, "Request was rejected by the backend."))
    if not response.ok:
        raise ApiError(_detail(response, f"Backend error ({response.status_code})."))

    if response.content:
        return response.json()
    return None


def list_documents() -> list[dict[str, Any]]:
    data = _request("GET", "/documents")
    return data.get("documents", []) if data else []


def upload_document(filename: str, file_bytes: bytes, content_type: str | None) -> dict[str, Any]:
    files = {"file": (filename, file_bytes, content_type or "application/octet-stream")}
    return _request("POST", "/documents/upload", files=files, timeout=60)


def ask_documents(question: str, top_k: int = 5) -> dict[str, Any]:
    return _request(
        "POST", "/documents/ask", json={"question": question, "top_k": top_k}, timeout=60
    )


def get_job(job_id: str) -> dict[str, Any]:
    return _request("GET", f"/documents/jobs/{job_id}")


def get_document_content(document_id: str) -> dict[str, Any]:
    return _request("GET", f"/documents/{document_id}/content")


def delete_document(document_id: str) -> dict[str, Any]:
    return _request("DELETE", f"/documents/{document_id}")


def reindex_document(document_id: str) -> dict[str, Any]:
    return _request("POST", f"/documents/{document_id}/reindex")


def list_reviews() -> list[dict[str, Any]]:
    data = _request("GET", "/reviews")
    return data if isinstance(data, list) else []


def list_suggestions() -> list[dict[str, Any]]:
    data = _request("GET", "/planning-suggestions")
    return data if isinstance(data, list) else []


def promote_suggestion(suggestion_id: str) -> dict[str, Any]:
    return _request("POST", f"/planning-suggestions/{suggestion_id}/promote")


def list_query_logs(limit: int = 100) -> list[dict[str, Any]]:
    data = _request("GET", "/admin/document-query-logs", params={"limit": limit})
    return data.get("logs", []) if data else []


def clear_query_logs() -> dict[str, Any]:
    return _request("POST", "/admin/document-query-logs/clear")


def list_risks() -> list[dict[str, Any]]:
    data = _request("GET", "/risks")
    return data if isinstance(data, list) else []


def scan_risks() -> list[dict[str, Any]]:
    # On-demand detection: refreshes the auto-detected findings, returns the stored set.
    # Generous timeout — LLM detection reads every document in one pass.
    data = _request("POST", "/admin/risks/detect", timeout=120)
    return data if isinstance(data, list) else []


def generate_jira_tasks(document_id: str | None = None) -> list[dict[str, Any]]:
    # Ephemeral Jira-task drafts generated from one document (or all documents when
    # document_id is None). Nothing is persisted; the Board renders these in-session.
    # Generous timeout — LLM generation reads the document text in one pass.
    data = _request(
        "POST", "/admin/jira-tasks/generate", json={"document_id": document_id}, timeout=120
    )
    return data if isinstance(data, list) else []
