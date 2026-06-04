from typing import Any

from clients.game_project_client import create_game_project_client
from settings import get_settings

settings = get_settings()

GAME_PROJECT_CLIENT = create_game_project_client(
    client_type=settings.game_project_client_type,
    base_url=settings.game_project_api_base_url,
    api_key=settings.game_project_api_key,
)


def get_task_status(task_id: str) -> dict[str, Any]:
    normalized_task_id = task_id.upper()
    task = GAME_PROJECT_CLIENT.get_task(normalized_task_id)

    if task is None:
        return {
            "found": False,
            "task_id": normalized_task_id,
            "message": "Task not found.",
        }

    return {
        "found": True,
        "task_id": normalized_task_id,
        "status": task["status"],
        "department": task["department"],
        "priority": task["priority"],
        "notes": task["notes"],
    }


def check_task_blockers(task_id: str) -> dict[str, Any]:
    normalized_task_id = task_id.upper()
    task = GAME_PROJECT_CLIENT.get_task(normalized_task_id)

    if task is None:
        return {
            "found": False,
            "task_id": normalized_task_id,
            "blocked": False,
            "reason": "Task not found.",
        }

    is_blocked = task["status"] == "blocked"

    return {
        "found": True,
        "task_id": normalized_task_id,
        "blocked": is_blocked,
        "assignable": task["assignable"],
        "reason": task["notes"],
    }


PENDING_TASK_UPDATES: dict[str, dict[str, object]] = {}


def create_pending_task_update(task_id: str) -> dict[str, object]:
    blocker_check = check_task_blockers(task_id)
    normalized_task_id = str(blocker_check["task_id"])

    if not blocker_check["found"]:
        return {
            "created": False,
            "task_id": normalized_task_id,
            "message": "Task update could not be staged because the task was not found.",
        }

    if not blocker_check["assignable"]:
        return {
            "created": False,
            "task_id": normalized_task_id,
            "message": (
                f"Task update could not be staged. Reason: {blocker_check['reason']}"
            ),
        }

    pending_action_id = f"PEND-{len(PENDING_TASK_UPDATES) + 1:03d}"

    pending_action: dict[str, object] = {
        "pending_action_id": pending_action_id,
        "task_id": normalized_task_id,
        "action": "update_task_status",
        "status": "pending_confirmation",
    }

    PENDING_TASK_UPDATES[pending_action_id] = pending_action

    return {
        "created": True,
        "pending_action_id": pending_action_id,
        "task_id": normalized_task_id,
        "action": "update_task_status",
        "status": "pending_confirmation",
        "message": "Task update is pending your confirmation.",
    }


TASK_UPDATES: list[dict[str, object]] = []


def confirm_pending_task_update(pending_action_id: str) -> dict[str, object]:
    pending_action = PENDING_TASK_UPDATES.get(pending_action_id)

    if pending_action is None:
        return {
            "confirmed": False,
            "pending_action_id": pending_action_id,
            "message": "Pending task update was not found.",
        }

    task_id = str(pending_action["task_id"])
    update_id = f"UPD-{len(TASK_UPDATES) + 1:03d}"

    task_update: dict[str, object] = {
        "update_id": update_id,
        "task_id": task_id,
        "status": "submitted",
    }

    TASK_UPDATES.append(task_update)
    del PENDING_TASK_UPDATES[pending_action_id]

    return {
        "confirmed": True,
        "pending_action_id": pending_action_id,
        "update_id": update_id,
        "task_id": task_id,
        "status": "submitted",
        "message": "Task update confirmed and submitted.",
    }
