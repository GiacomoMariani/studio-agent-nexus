import urllib.error

import pytest

from clients.game_project_client import (
    FallbackGameProjectClient,
    GameProjectClientError,
    HttpGameProjectClient,
    LocalGameProjectClient,
    create_game_project_client,
)


class FakeHttpResponse:
    def __init__(self, body: str):
        self.body = body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def read(self) -> bytes:
        return self.body


class FakeSuccessfulGameProjectClient:
    def get_task(self, task_id: str):
        return {
            "status": "from-primary",
            "department": "Code",
            "priority": "High",
            "assignable": True,
            "notes": "Primary client result.",
        }


class FakeFailingGameProjectClient:
    def get_task(self, task_id: str):
        raise GameProjectClientError("Primary client failed.")


class FakeMissingGameProjectClient:
    def get_task(self, task_id: str):
        return None


def test_local_client_returns_existing_task():
    client = LocalGameProjectClient()

    task = client.get_task("TASK-001")

    assert task is not None
    assert task["status"] == "in_progress"
    assert task["department"] == "Code"
    assert task["priority"] == "High"


def test_local_client_normalizes_task_id():
    client = LocalGameProjectClient()

    task = client.get_task("task-001")

    assert task is not None
    assert task["status"] == "in_progress"


def test_local_client_returns_none_for_missing_task():
    client = LocalGameProjectClient()

    task = client.get_task("TASK-999")

    assert task is None


def test_local_client_returns_copy_of_task_data():
    client = LocalGameProjectClient()

    task = client.get_task("TASK-001")
    assert task is not None

    task["status"] = "changed"

    fresh_task = client.get_task("TASK-001")

    assert fresh_task is not None
    assert fresh_task["status"] == "in_progress"


def test_create_client_returns_local_client_by_default():
    client = create_game_project_client()

    assert isinstance(client, LocalGameProjectClient)


def test_create_client_returns_http_client():
    client = create_game_project_client(
        client_type="http",
        base_url="https://projects.example.com",
        api_key="secret-token",
    )

    assert isinstance(client, HttpGameProjectClient)
    assert client.base_url == "https://projects.example.com"
    assert client.api_key == "secret-token"


def test_create_client_requires_base_url_for_http():
    with pytest.raises(GameProjectClientError) as error:
        create_game_project_client(client_type="http")

    assert "GAME_PROJECT_API_BASE_URL is required" in str(error.value)


def test_create_client_rejects_unknown_client_type():
    with pytest.raises(GameProjectClientError) as error:
        create_game_project_client(client_type="something-else")

    assert "Unsupported game project client type" in str(error.value)


def test_http_client_retries_retryable_http_error_then_succeeds(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request)

        if len(calls) == 1:
            raise urllib.error.HTTPError(
                url=request.full_url,
                code=503,
                msg="Service Unavailable",
                hdrs=None,
                fp=None,
            )

        return FakeHttpResponse(
            '{"status": "in_progress", "department": "Code",'
            ' "priority": "High", "assignable": true,'
            ' "notes": "Retried successfully."}'
        )

    monkeypatch.setattr(
        "clients.game_project_client.urllib.request.urlopen",
        fake_urlopen,
    )

    client = HttpGameProjectClient(
        base_url="https://projects.example.com",
        max_retries=1,
        retry_delay_seconds=0,
    )

    task = client.get_task("task-001")

    assert task is not None
    assert task["status"] == "in_progress"
    assert len(calls) == 2


def test_http_client_uses_retry_after_header_for_429(monkeypatch):
    calls = []
    sleep_delays = []

    def fake_sleep(delay):
        sleep_delays.append(delay)

    def fake_urlopen(request, timeout):
        calls.append(request)

        if len(calls) == 1:
            raise urllib.error.HTTPError(
                url=request.full_url,
                code=429,
                msg="Too Many Requests",
                hdrs={"Retry-After": "2"},
                fp=None,
            )

        return FakeHttpResponse(
            '{"status": "in_progress", "department": "Code",'
            ' "priority": "High", "assignable": true, "notes": "Ok."}'
        )

    monkeypatch.setattr(
        "clients.game_project_client.urllib.request.urlopen",
        fake_urlopen,
    )
    monkeypatch.setattr(
        "clients.game_project_client.time.sleep",
        fake_sleep,
    )

    client = HttpGameProjectClient(
        base_url="https://projects.example.com",
        max_retries=1,
        retry_delay_seconds=0,
    )

    task = client.get_task("TASK-001")

    assert task is not None
    assert len(calls) == 2
    assert sleep_delays == [2.0]


def test_http_client_caps_retry_after_delay_for_429(monkeypatch):
    calls = []
    sleep_delays = []

    def fake_sleep(delay):
        sleep_delays.append(delay)

    def fake_urlopen(request, timeout):
        calls.append(request)

        if len(calls) == 1:
            raise urllib.error.HTTPError(
                url=request.full_url,
                code=429,
                msg="Too Many Requests",
                hdrs={"Retry-After": "999"},
                fp=None,
            )

        return FakeHttpResponse(
            '{"status": "in_progress", "department": "Code",'
            ' "priority": "High", "assignable": true, "notes": "Ok."}'
        )

    monkeypatch.setattr(
        "clients.game_project_client.urllib.request.urlopen",
        fake_urlopen,
    )
    monkeypatch.setattr(
        "clients.game_project_client.time.sleep",
        fake_sleep,
    )

    client = HttpGameProjectClient(
        base_url="https://projects.example.com",
        max_retries=1,
        retry_delay_seconds=0,
        max_retry_delay_seconds=5,
    )

    task = client.get_task("TASK-001")

    assert task is not None
    assert len(calls) == 2
    assert sleep_delays == [5.0]


def test_http_client_returns_none_for_404_without_retrying(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request)

        raise urllib.error.HTTPError(
            url=request.full_url,
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(
        "clients.game_project_client.urllib.request.urlopen",
        fake_urlopen,
    )

    client = HttpGameProjectClient(
        base_url="https://projects.example.com",
        max_retries=2,
        retry_delay_seconds=0,
    )

    task = client.get_task("TASK-999")

    assert task is None
    assert len(calls) == 1


def test_http_client_raises_after_retryable_errors_exhausted(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request)

        raise urllib.error.HTTPError(
            url=request.full_url,
            code=503,
            msg="Service Unavailable",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(
        "clients.game_project_client.urllib.request.urlopen",
        fake_urlopen,
    )

    client = HttpGameProjectClient(
        base_url="https://projects.example.com",
        max_retries=2,
        retry_delay_seconds=0,
    )

    with pytest.raises(GameProjectClientError) as error:
        client.get_task("TASK-001")

    assert "Game project API returned HTTP 503" in str(error.value)
    assert len(calls) == 3


def test_fallback_client_uses_primary_when_primary_succeeds():
    client = FallbackGameProjectClient(
        primary_client=FakeSuccessfulGameProjectClient(),
        fallback_client=LocalGameProjectClient(),
    )

    task = client.get_task("TASK-001")

    assert task is not None
    assert task["status"] == "from-primary"


def test_fallback_client_uses_fallback_when_primary_fails():
    client = FallbackGameProjectClient(
        primary_client=FakeFailingGameProjectClient(),
        fallback_client=LocalGameProjectClient(),
    )

    task = client.get_task("TASK-001")

    assert task is not None
    assert task["status"] == "in_progress"


def test_fallback_client_does_not_fallback_when_primary_returns_none():
    client = FallbackGameProjectClient(
        primary_client=FakeMissingGameProjectClient(),
        fallback_client=LocalGameProjectClient(),
    )

    task = client.get_task("TASK-001")

    assert task is None


def test_create_client_returns_http_with_fallback():
    client = create_game_project_client(
        client_type="http_with_fallback",
        base_url="https://projects.example.com",
        api_key="secret-token",
    )

    assert isinstance(client, FallbackGameProjectClient)
    assert isinstance(client.primary_client, HttpGameProjectClient)
    assert isinstance(client.fallback_client, LocalGameProjectClient)
