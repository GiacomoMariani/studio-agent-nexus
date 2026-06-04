"""Mock demo data for Studio Agent Nexus.

Only the still-mock surfaces keep fixtures here:
- ``SAMPLE_QUESTIONS`` — demo prompts for the Ask page.
- ``BOARD_STATES`` / ``REVIEW_STATES`` / ``VIEW_STATES`` — board state labels/colours.

Wired pages (Upload, Ask, Board, Logs, Risks) read real API data, not fixtures.
"""

SAMPLE_QUESTIONS: list[str] = [
    "How does the matchmaking service work?",
    "What is the authoritative server tick rate?",
    "Which data stores does the backend use?",
    "Who owns the event pipeline?",
    "What is blocking the beta release?",
    "How is D1 retention defined?",
]

BOARD_STATES: list[dict[str, str]] = [
    {"id": "ai", "label": "Ready for AI review", "color": "#14B8A6"},
    {"id": "lead", "label": "Ready for tech-lead review", "color": "#8B5CF6"},
    {"id": "backlog", "label": "Backlog", "color": "#64748B"},
    {"id": "todo", "label": "To Do", "color": "#3B82F6"},
    {"id": "doing", "label": "Doing", "color": "#F59E0B"},
    {"id": "done", "label": "Done", "color": "#22C55E"},
]
REVIEW_STATES: list[str] = ["ai", "lead"]
VIEW_STATES: list[str] = ["backlog", "todo", "doing", "done"]
