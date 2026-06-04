"""API tests for the unified query log (cost fields written on ask) + clear endpoint."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

AUTH = {"X-API-Key": "test-secret-key"}


def test_ask_writes_model_and_cost_into_query_log():
    asked = client.post(
        "/documents/ask", headers=AUTH, json={"question": "What is the tick rate?", "top_k": 3}
    )
    assert asked.status_code == 200

    logs = client.get("/admin/document-query-logs", headers=AUTH).json()["logs"]
    assert len(logs) >= 1

    log = logs[0]
    assert log["model_name"] == "rule-based"  # default answerer
    assert log["input_tokens"] > 0
    assert "output_tokens" in log
    assert log["estimated_cost_usd"] > 0  # notional cost even for the free local answerer


def test_clear_endpoint_empties_logs():
    client.post("/documents/ask", headers=AUTH, json={"question": "hello there", "top_k": 3})
    assert client.get("/admin/document-query-logs", headers=AUTH).json()["logs"]

    cleared = client.post("/admin/document-query-logs/clear", headers=AUTH)
    assert cleared.status_code == 200
    assert cleared.json() == {"cleared": True}

    assert client.get("/admin/document-query-logs", headers=AUTH).json()["logs"] == []


def test_clear_requires_api_key():
    assert client.post("/admin/document-query-logs/clear").status_code == 401
