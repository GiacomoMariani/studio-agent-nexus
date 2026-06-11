"""API tests for GET /documents/{id}/content — the source-download endpoint."""

import main
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
AUTH = {"X-API-Key": "test-secret-key"}


def _seed(filename: str = "guide.md", text: str = "# Guide\nFastAPI is the framework."):
    return main.sqlite_document_store.save_document(
        filename=filename, text=text, chunk_payloads=[], is_demo=True,
    )


def test_requires_api_key():
    doc = _seed()
    assert client.get(f"/documents/{doc.document_id}/content").status_code == 401


def test_returns_document_content():
    doc = _seed(filename="arch.md", text="# Arch\nServers and data stores.")

    response = client.get(f"/documents/{doc.document_id}/content", headers=AUTH)

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == doc.document_id
    assert body["filename"] == "arch.md"
    assert body["file_type"] == "md"
    assert body["content"] == "# Arch\nServers and data stores."


def test_unknown_document_returns_404():
    response = client.get("/documents/doc-does-not-exist/content", headers=AUTH)
    assert response.status_code == 404
