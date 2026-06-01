import re
from typing import Any

from tools.production_tools import (
    check_task_blockers,
    confirm_pending_task_update,
    create_pending_task_update,
    get_task_status,
)


TASK_ID_PATTERN = re.compile(r"\bTASK-\d+\b", re.IGNORECASE)
PENDING_ACTION_PATTERN = re.compile(r"\bPEND-\d+\b", re.IGNORECASE)

TOOL_GET_TASK_STATUS = "get_task_status"
TOOL_CHECK_TASK_BLOCKERS = "check_task_blockers"
TOOL_CREATE_PENDING_TASK_UPDATE = "create_pending_task_update"
TOOL_CONFIRM_PENDING_TASK_UPDATE = "confirm_pending_task_update"


class ToolAssistantService:
    async def answer(self, message: str) -> dict[str, Any]:
        pending_action_id = self._extract_pending_action_id(message)

        if pending_action_id and self._is_confirmation(message):
            return self._handle_pending_task_confirmation(pending_action_id)

        task_id = self._extract_task_id(message)

        if task_id is None:
            return self._build_response(
                answer="Please provide a task ID so I can help with your request.",
                tool_calls=[],
            )

        if self._is_update_request(message):
            return self._handle_pending_task_creation(task_id)

        if self._is_blocker_question(message):
            tool_result = check_task_blockers(task_id)

            return self._build_response(
                answer=self._format_blocker_answer(tool_result),
                tool_calls=[
                    {
                        "tool_name": TOOL_CHECK_TASK_BLOCKERS,
                        "result": tool_result,
                    }
                ],
            )

        tool_result = get_task_status(task_id)

        return self._build_response(
            answer=self._format_status_answer(tool_result),
            tool_calls=[
                {
                    "tool_name": TOOL_GET_TASK_STATUS,
                    "result": tool_result,
                }
            ],
        )

    def _handle_pending_task_creation(self, task_id: str) -> dict[str, Any]:
        tool_result = create_pending_task_update(task_id)

        return self._build_response(
            answer=self._format_pending_task_creation_answer(tool_result),
            tool_calls=[
                {
                    "tool_name": TOOL_CREATE_PENDING_TASK_UPDATE,
                    "result": tool_result,
                }
            ],
        )

    def _handle_pending_task_confirmation(self, pending_action_id: str) -> dict[str, Any]:
        tool_result = confirm_pending_task_update(pending_action_id)

        return self._build_response(
            answer=self._format_pending_task_confirmation_answer(tool_result),
            tool_calls=[
                {
                    "tool_name": TOOL_CONFIRM_PENDING_TASK_UPDATE,
                    "result": tool_result,
                }
            ],
        )

    def _build_response(
        self,
        answer: str,
        tool_calls: list[dict[str, Any]],
    ) -> dict[str, Any]:
        last_tool_call = tool_calls[-1] if tool_calls else None

        return {
            "answer": answer,
            "tool_called": last_tool_call["tool_name"] if last_tool_call else None,
            "tool_result": last_tool_call["result"] if last_tool_call else None,
            "tool_calls": tool_calls,
        }

    def _extract_task_id(self, message: str) -> str | None:
        match = TASK_ID_PATTERN.search(message)

        if match is None:
            return None

        return match.group(0).upper()

    def _extract_pending_action_id(self, message: str) -> str | None:
        match = PENDING_ACTION_PATTERN.search(message)

        if match is None:
            return None

        return match.group(0).upper()

    def _is_confirmation(self, message: str) -> bool:
        normalized_message = message.lower()

        confirmation_terms = [
            "confirm",
            "yes",
            "approve",
            "go ahead",
            "submit",
        ]

        return any(term in normalized_message for term in confirmation_terms)

    def _is_blocker_question(self, message: str) -> bool:
        normalized_message = message.lower()

        blocker_terms = [
            "blocked",
            "blocker",
            "blocking",
            "can i assign",
            "assignable",
        ]

        return any(term in normalized_message for term in blocker_terms)

    def _is_update_request(self, message: str) -> bool:
        normalized_message = message.lower()

        update_terms = [
            "update this task",
            "update task",
            "mark as done",
            "mark complete",
            "close this task",
            "close task",
            "submit an update",
        ]

        return any(term in normalized_message for term in update_terms)

    def _format_status_answer(self, tool_result: dict[str, object]) -> str:
        if not tool_result["found"]:
            return f"I could not find task {tool_result['task_id']}."

        return (
            f"Task {tool_result['task_id']} is currently {tool_result['status']}. "
            f"Department: {tool_result['department']}. "
            f"Priority: {tool_result['priority']}. "
            f"Notes: {tool_result['notes']}"
        )

    def _format_blocker_answer(self, tool_result: dict[str, object]) -> str:
        if not tool_result["found"]:
            return f"I could not find task {tool_result['task_id']}."

        if tool_result["blocked"]:
            return (
                f"Task {tool_result['task_id']} is currently blocked and cannot be "
                f"assigned. Reason: {tool_result['reason']}"
            )

        return (
            f"Task {tool_result['task_id']} has no blockers and is assignable. "
            f"Notes: {tool_result['reason']}"
        )

    def _format_pending_task_creation_answer(
        self,
        tool_result: dict[str, object],
    ) -> str:
        if not tool_result["created"]:
            return str(tool_result["message"])

        return (
            f"Task {tool_result['task_id']} is ready for an update. "
            f"Please confirm {tool_result['pending_action_id']} if you want me "
            f"to submit the task update."
        )

    def _format_pending_task_confirmation_answer(
        self,
        tool_result: dict[str, object],
    ) -> str:
        if not tool_result["confirmed"]:
            return str(tool_result["message"])

        return (
            f"Task update {tool_result['update_id']} has been submitted "
            f"for task {tool_result['task_id']}."
        )
