"""Mock demo data for Studio Agent Nexus.

Ported verbatim from the Claude Design prototype
(`tickets/_design-sample/studio-agent-nexus.html`). Pages without a backend use this
data directly; wired pages (Upload, Ask, Logs) swap it for real API calls per ticket.
"""

from typing import Any

DEMO_DOCS: list[dict[str, Any]] = [
    {"id": "d1", "name": "combat_system_v2.md", "type": "MD", "status": "Indexed", "chunks": 24, "demo": True},
    {"id": "d2", "name": "enemy_ai_spec.pdf", "type": "PDF", "status": "Indexed", "chunks": 31, "demo": True},
    {"id": "d3", "name": "playtest_notes_build47.md", "type": "MD", "status": "Indexed", "chunks": 18, "demo": False},
    {"id": "d4", "name": "economy_balance.pdf", "type": "PDF", "status": "Processing", "chunks": 12, "demo": False},
]

SAMPLE_QUESTIONS: list[str] = [
    "What changes were made to the combo system?",
    "How does enemy aggression scale with difficulty?",
    "What did playtesters say about the tutorial pacing?",
    "Are there any open issues with the parry window?",
    "What is the target frame budget for combat?",
    "Which systems depend on the state machine refactor?",
]

GROUNDED_ANSWER: dict[str, Any] = {
    "mode": "openai",
    "question": "What changes were made to the combo system?",
    "text": (
        "The combo system was reworked in v2 to use a buffered input queue instead of "
        "strict frame-window timing. Inputs are now captured up to 6 frames early and "
        "flushed on the next valid attack state, which playtesters found significantly "
        "more forgiving. The combo counter also resets on a 0.8s idle timeout rather "
        "than on any missed input, and successful finishers now grant a short damage "
        "multiplier window."
    ),
    "sources": [
        {
            "file": "combat_system_v2.md",
            "snippet": (
                "Buffered input queue replaces strict frame-window matching. Inputs are "
                "captured up to 6 frames early and flushed on the next valid attack "
                "state. Combo counter resets on a 0.8s idle timeout rather than on any "
                "single missed input."
            ),
            "score": 0.91,
        },
        {
            "file": "playtest_notes_build47.md",
            "snippet": (
                "Players reported the new combo timing feels 'much more forgiving' than "
                "build 41. Finisher damage window was called out positively in 7 of 9 "
                "sessions."
            ),
            "score": 0.84,
        },
    ],
}

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

DEMO_TASKS: list[dict[str, Any]] = [
    {"dept": "Code", "priority": "Critical", "title": "Refactor combat state machine to support input buffering", "desc": "Current state machine cannot queue inputs across attack states. Required before combo v2 ships.", "source": "combat_system_v2.md", "state": "ai", "github": {"kind": "pr", "pr": "PR #142", "branch": "feature/combat-fsm", "status": "Checks passing · 1 approval", "tone": "ok"}},
    {"dept": "QA", "priority": "Critical", "title": "Build regression suite for parry timing", "desc": "Parry window changed between builds; needs automated coverage to prevent regressions.", "source": "playtest_notes_build47.md", "state": "ai", "github": {"kind": "pr", "pr": "PR #138", "branch": "qa/parry-suite", "status": "CI failing", "tone": "bad"}},
    {"dept": "Production", "priority": "High", "title": "Sequence combat rework ahead of economy pass", "desc": "Combat changes affect encounter pacing, which feeds reward tuning. Order accordingly.", "source": "economy_balance.pdf", "state": "lead", "github": {"kind": "pr", "pr": "PR #131", "branch": "prod/sequencing", "status": "Changes requested", "tone": "warn"}},
    {"dept": "Code", "priority": "High", "title": "Implement 6-frame input buffer with idle-timeout reset", "desc": "Capture inputs early and flush on next valid attack state; reset combo counter after 0.8s idle.", "source": "combat_system_v2.md", "state": "todo", "github": {"kind": "branch", "branch": "feature/input-buffer", "status": "Branch pushed · no PR yet", "tone": "warn"}},
    {"dept": "QA", "priority": "Medium", "title": "Verify combo counter reset across all weapon types", "desc": "Confirm 0.8s idle reset behaves consistently for light, heavy, and ranged weapons.", "source": "combat_system_v2.md", "state": "todo", "github": {"kind": "commit", "commit": "a3f9c2", "branch": "main", "status": "Committed to main", "tone": "neutral"}},
    {"dept": "Art", "priority": "Medium", "title": "Add VFX flourish for finisher damage window", "desc": "Visual feedback to communicate the active multiplier state to players.", "source": "playtest_notes_build47.md", "state": "doing", "github": {"kind": "branch", "branch": "art/finisher-vfx", "status": "Branch pushed · no PR yet", "tone": "warn"}},
    {"dept": "Design", "priority": "High", "title": "Re-tune enemy aggression curve for Normal difficulty", "desc": "Playtesters found mid-game encounters spike unexpectedly. Smooth the aggression ramp.", "source": "enemy_ai_spec.pdf", "state": "backlog", "github": {"kind": "none"}},
    {"dept": "Design", "priority": "Medium", "title": "Define finisher damage-multiplier window values", "desc": "Specify duration and multiplier for the post-finisher damage window across weapon classes.", "source": "combat_system_v2.md", "state": "backlog", "github": {"kind": "none"}},
    {"dept": "Art", "priority": "Low", "title": "Polish enemy telegraph animations for heavy attacks", "desc": "Telegraphs read inconsistently at distance per playtest feedback.", "source": "enemy_ai_spec.pdf", "state": "backlog", "github": {"kind": "none"}},
    {"dept": "Production", "priority": "Low", "title": "Schedule a focused parry-feel playtest for build 48", "desc": "Validate parry changes with a fresh cohort before locking the window.", "source": "playtest_notes_build47.md", "state": "done", "github": {"kind": "merged", "pr": "PR #120", "branch": "prod/playtest-48", "status": "Merged", "tone": "ok"}},
]

# Net-new tasks the planning add-on proposes — work the documents imply but the to-do is missing.
SUGGESTED_TASKS: list[dict[str, str]] = [
    {"dept": "QA", "priority": "Critical", "title": "Document the exact parry-window frame value", "reason": "Referenced across the combat and playtest docs but never quantified — blocks the parry regression suite."},
    {"dept": "Design", "priority": "High", "title": "Define enemy aggression target values for Normal", "reason": "The aggression re-tune task has no numeric targets to hit."},
    {"dept": "Code", "priority": "High", "title": "Reconcile combo-reset rule with enemy stagger logic", "reason": "The combat spec and enemy AI spec disagree on when the combo resets."},
    {"dept": "Design", "priority": "Medium", "title": "Specify finisher damage-multiplier values per weapon class", "reason": "The multiplier window is described qualitatively but never given values."},
    {"dept": "Production", "priority": "Medium", "title": "Add tutorial coverage for input buffering", "reason": "Onboarding still teaches strict-timing combos; the new feel is untaught."},
]

DEMO_RISKS: list[dict[str, Any]] = [
    {"kind": "risk", "severity": "Critical", "title": "Parry window value is undocumented", "desc": "The combat spec references a 'tightened parry window' but no concrete frame value is recorded anywhere. QA cannot write deterministic tests against an unspecified value.", "source": "combat_system_v2.md"},
    {"kind": "risk", "severity": "High", "title": "Economy pass blocked by combat pacing changes", "desc": "Reward tuning depends on encounter length, which the combat rework will change. Starting the economy pass now risks rework.", "source": "economy_balance.pdf"},
    {"kind": "risk", "severity": "Medium", "title": "Tutorial does not cover new input buffering", "desc": "Onboarding still teaches strict-timing combos. New players may be confused by the changed feel.", "source": "playtest_notes_build47.md"},
    {"kind": "contradiction", "severity": "Critical", "title": "Conflicting combo-reset behaviour", "a": {"file": "combat_system_v2.md", "text": "Combo counter resets on a 0.8s idle timeout rather than on any single missed input."}, "b": {"file": "enemy_ai_spec.pdf", "text": "Enemy stagger assumes the player combo resets immediately on any whiffed attack."}},
    {"kind": "contradiction", "severity": "High", "title": "Disagreement on target frame budget", "a": {"file": "combat_system_v2.md", "text": "Combat must hold a 4ms CPU budget per frame on target hardware."}, "b": {"file": "enemy_ai_spec.pdf", "text": "Enemy AI evaluation alone is allocated 5ms per frame in the perf plan."}},
]

# Persisted interaction logs: question asked, answer returned, and cost incurred.
DEMO_QUERY_LOG: list[dict[str, Any]] = [
    {"id": "q-2041", "ts": "2026-06-01 14:32:08", "q": "What changes were made to the combo system?", "mode": "openai", "model": "gpt-4.1-mini", "answer": "The combo system was reworked in v2 to use a buffered input queue instead of strict frame-window timing. Inputs are captured up to 6 frames early and flushed on the next valid attack state, and the combo counter now resets on a 0.8s idle timeout rather than on any missed input.", "promptTok": 1242, "completionTok": 184, "cost": 0.0008, "cites": 2, "fallback": False, "latency": 312},
    {"id": "q-2040", "ts": "2026-06-01 14:30:51", "q": "How does enemy aggression scale with difficulty?", "mode": "openai", "model": "gpt-4.1-mini", "answer": "Aggression scales through a per-difficulty multiplier on attack frequency and approach speed. Normal difficulty currently spikes in mid-game encounters, which the aggression re-tune task is meant to smooth.", "promptTok": 1190, "completionTok": 206, "cost": 0.0008, "cites": 3, "fallback": False, "latency": 401},
    {"id": "q-2039", "ts": "2026-06-01 14:28:19", "q": "What is the studio's remote work policy?", "mode": "local", "model": "rule-based", "answer": "Not found in uploaded documents. The agent declined rather than inventing an answer.", "promptTok": 0, "completionTok": 0, "cost": 0.0000, "cites": 0, "fallback": True, "latency": 188},
    {"id": "q-2038", "ts": "2026-06-01 14:25:44", "q": "What did playtesters say about tutorial pacing?", "mode": "openai", "model": "gpt-4.1-mini", "answer": "Playtesters found the tutorial slightly slow in the first third but clear overall. Most pacing complaints centred on repeated combo drills rather than the explanations themselves.", "promptTok": 980, "completionTok": 142, "cost": 0.0006, "cites": 1, "fallback": False, "latency": 256},
    {"id": "q-2037", "ts": "2026-06-01 14:21:02", "q": "Which systems depend on the state machine refactor?", "mode": "openai", "model": "gpt-4.1-mini", "answer": "Input buffering, combo counting, and the finisher damage window all depend on the state-machine refactor landing first, which is why it is sequenced ahead of the rest of combat v2.", "promptTok": 1105, "completionTok": 168, "cost": 0.0007, "cites": 2, "fallback": False, "latency": 377},
    {"id": "q-2036", "ts": "2026-06-01 14:18:30", "q": "What is the marketing launch date?", "mode": "local", "model": "rule-based", "answer": "Not found in uploaded documents.", "promptTok": 0, "completionTok": 0, "cost": 0.0000, "cites": 0, "fallback": True, "latency": 164},
    {"id": "q-2035", "ts": "2026-06-01 14:15:55", "q": "What is the target frame budget for combat?", "mode": "openai", "model": "gpt-4.1-mini", "answer": "Combat must hold a 4ms CPU budget per frame on target hardware. Note this conflicts with the enemy-AI allocation of 5ms recorded in the AI spec — flagged as a contradiction.", "promptTok": 1060, "completionTok": 150, "cost": 0.0007, "cites": 2, "fallback": False, "latency": 344},
]

# Running aggregate of the full store (the list above is the most recent slice).
LOG_SUMMARY: dict[str, Any] = {"stored": 127, "totalCost": 0.41, "avgCost": 0.0032, "tokens": "1.21M", "fallbackRate": "6%"}

KNOWLEDGE_GAPS: list[dict[str, str]] = [
    {"q": "What is the studio's remote work policy?", "ts": "14:28:19"},
    {"q": "What is the marketing launch date?", "ts": "14:18:30"},
    {"q": "How many seats does our Jira license cover?", "ts": "13:54:11"},
]
