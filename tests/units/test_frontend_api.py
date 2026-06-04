"""Unit tests for the frontend HTTP client (frontend/api.py).

Uses a fake `requests.request` so no backend is needed.
"""

import sys
from pathlib import Path

import pytest

FRONTEND_DIR = str(Path(__file__).resolve().parents[2] / "frontend")
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

import api  # noqa: E402


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, content=b"{}"):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.content = content

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        return self._json


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("APP_API_KEY", "test-key")
    monkeypatch.setenv("API_BASE_URL", "http://backend:8000")


def _capture(monkeypatch, response):
    calls = {}

    def fake_request(method, url, **kwargs):
        calls["method"] = method
        calls["url"] = url
        calls["kwargs"] = kwargs
        return response

    monkeypatch.setattr(api.requests, "request", fake_request)
    return calls


def test_list_documents_returns_list(monkeypatch):
    calls = _capture(
        monkeypatch,
        FakeResponse(json_data={"documents": [{"document_id": "d1"}]}),
    )
    docs = api.list_documents()
    assert docs == [{"document_id": "d1"}]
    assert calls["method"] == "GET"
    assert calls["url"] == "http://backend:8000/documents"
    assert calls["kwargs"]["headers"]["X-API-Key"] == "test-key"


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("APP_API_KEY", raising=False)
    with pytest.raises(api.ApiError, match="APP_API_KEY"):
        api.list_documents()


def test_unreachable_backend_raises(monkeypatch):
    def boom(method, url, **kwargs):
        raise api.requests.RequestException("connection refused")

    monkeypatch.setattr(api.requests, "request", boom)
    with pytest.raises(api.ApiError, match="Could not reach the backend"):
        api.list_documents()


def test_unauthorized_maps_to_clean_error(monkeypatch):
    _capture(monkeypatch, FakeResponse(status_code=401))
    with pytest.raises(api.ApiError, match="Unauthorized"):
        api.list_documents()


def test_403_surfaces_backend_detail(monkeypatch):
    _capture(
        monkeypatch,
        FakeResponse(status_code=403, json_data={"detail": "Demo documents cannot be deleted."}),
    )
    with pytest.raises(api.ApiError, match="Demo documents cannot be deleted."):
        api.delete_document("d1")


def test_upload_sends_multipart(monkeypatch):
    calls = _capture(monkeypatch, FakeResponse(json_data={"job_id": "j1", "status": "queued"}))
    job = api.upload_document("notes.md", b"hello", "text/markdown")
    assert job["job_id"] == "j1"
    assert calls["method"] == "POST"
    assert calls["url"].endswith("/documents/upload")
    assert "files" in calls["kwargs"]
