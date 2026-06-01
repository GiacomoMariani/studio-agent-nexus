from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

AUTH_HEADERS = {"X-API-Key": "test-secret-key"}


def test_tool_assistant_returns_task_status():
    response = client.post(
        "/tool-assistant",
        headers=AUTH_HEADERS,
        json={"message": "What is the status of TASK-001?"},
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["tool_called"] == "get_task_status"
    assert payload["tool_result"]["found"] is True
    assert payload["tool_result"]["task_id"] == "TASK-001"
    assert payload["tool_result"]["status"] == "in_progress"
    assert "currently in_progress" in payload["answer"]


def test_tool_assistant_checks_task_blockers():
    response = client.post(
        "/tool-assistant",
        headers=AUTH_HEADERS,
        json={"message": "Is TASK-002 blocked?"},
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["tool_called"] == "check_task_blockers"
    assert payload["tool_result"]["found"] is True
    assert payload["tool_result"]["task_id"] == "TASK-002"
    assert payload["tool_result"]["blocked"] is True
    assert "blocked" in payload["answer"]


def test_tool_assistant_asks_for_task_id_when_missing():
    response = client.post(
        "/tool-assistant",
        headers=AUTH_HEADERS,
        json={"message": "What is the status of my task?"},
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["tool_called"] is None
    assert payload["tool_result"] is None
    assert payload["answer"] == "Please provide a task ID so I can help with your request."


def test_tool_assistant_requires_api_key():
    response = client.post(
        "/tool-assistant",
        json={"message": "What is the status of TASK-001?"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key."}


def test_tool_assistant_creates_pending_task_update_when_assignable():
    response = client.post(
        "/tool-assistant",
        headers=AUTH_HEADERS,
        json={"message": "Please update task TASK-001."},
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["tool_called"] == "create_pending_task_update"
    assert payload["tool_result"]["created"] is True
    assert payload["tool_result"]["task_id"] == "TASK-001"
    assert payload["tool_result"]["status"] == "pending_confirmation"
    assert payload["tool_result"]["pending_action_id"].startswith("PEND-")

    assert len(payload["tool_calls"]) == 1
    assert payload["tool_calls"][0]["tool_name"] == "create_pending_task_update"
    assert payload["tool_calls"][0]["result"]["created"] is True

    assert "Please confirm" in payload["answer"]
    assert "if you want me to submit the task update" in payload["answer"]


def test_tool_assistant_confirms_pending_task_update():
    setup_response = client.post(
        "/tool-assistant",
        headers=AUTH_HEADERS,
        json={"message": "Please update task TASK-001."},
    )

    assert setup_response.status_code == 200

    setup_payload = setup_response.json()
    pending_action_id = setup_payload["tool_result"]["pending_action_id"]

    confirm_response = client.post(
        "/tool-assistant",
        headers=AUTH_HEADERS,
        json={"message": f"Confirm {pending_action_id}."},
    )

    assert confirm_response.status_code == 200

    payload = confirm_response.json()

    assert payload["tool_called"] == "confirm_pending_task_update"
    assert payload["tool_result"]["confirmed"] is True
    assert payload["tool_result"]["pending_action_id"] == pending_action_id
    assert payload["tool_result"]["task_id"] == "TASK-001"
    assert payload["tool_result"]["update_id"].startswith("UPD-")

    assert len(payload["tool_calls"]) == 1
    assert payload["tool_calls"][0]["tool_name"] == "confirm_pending_task_update"

    assert "Task update" in payload["answer"]
    assert "has been submitted" in payload["answer"]


def test_tool_assistant_does_not_create_pending_update_when_not_assignable():
    response = client.post(
        "/tool-assistant",
        headers=AUTH_HEADERS,
        json={"message": "Please update task TASK-002."},
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["tool_called"] == "create_pending_task_update"
    assert payload["tool_result"]["created"] is False
    assert payload["tool_result"]["task_id"] == "TASK-002"

    assert len(payload["tool_calls"]) == 1
    assert payload["tool_calls"][0]["tool_name"] == "create_pending_task_update"
    assert payload["tool_calls"][0]["result"]["created"] is False

    assert "could not be staged" in payload["answer"]
