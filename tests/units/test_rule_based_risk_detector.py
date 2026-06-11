"""RuleBasedRiskDetector must surface the seven planted demo findings (ticket-011).

Fixture text mirrors the real evidence sentences in the seven Game-Title docs; the detector
pulls the actual sentence out and emits a finding only when the evidence is present.
"""

from types import SimpleNamespace

import pytest

from services.rule_based_risk_detector import RuleBasedRiskDetector

ARCH_TEXT = (
    "Simulation tick rate: the authoritative simulation runs at 30 Hz (one tick every 33 ms). "
    "The target matchmaking time is p95 under 15 seconds at expected concurrency."
)
FLEET_TEXT = (
    "For sizing, the fleet model assumes each server instance runs the simulation at 60 Hz. "
    "There is currently no hard upper bound on how many instances autoscaling may request, "
    "so capacity planning and saturation alerts cannot be set."
)
PIPE_TEXT = (
    "Daily metrics are bucketed by UTC calendar day; for example, D1 retention is computed "
    "against the next calendar day after install, not a rolling 24-hour window. "
    "The purge window for player-identifying (PII) event fields is not specified."
)
ANALYTICS_TEXT = (
    "D1 retention counts a player as retained if they return within a rolling 24-hour window "
    "from the install timestamp. "
    "Ad revenue metrics depend on a player consent flag that is not yet wired through the client SDK."
)
READINESS_TEXT = (
    "The go-live SLA requires matchmaking p95 under 10 seconds, but the current architecture "
    "target is 15 seconds. "
    "The staging environment that mirrors production has not been provisioned."
)


def _doc(filename: str, text: str) -> SimpleNamespace:
    return SimpleNamespace(filename=filename, original_text=text)


DEMO_DOCS = [
    _doc("backend_architecture_overview.md", ARCH_TEXT),
    _doc("server_fleet_runbook.pdf", FLEET_TEXT),
    _doc("data_pipeline_spec.pdf", PIPE_TEXT),
    _doc("player_analytics_and_metrics.pdf", ANALYTICS_TEXT),
    _doc("release_readiness_checklist.md", READINESS_TEXT),
]

EXPECTED_IDS = {
    "auto-contradiction-tick-rate": "Critical",
    "auto-contradiction-matchmaking-sla": "High",
    "auto-contradiction-retention-definition": "Medium",
    "auto-risk-fleet-ceiling": "Critical",
    "auto-risk-pii-retention": "High",
    "auto-risk-staging-blocker": "High",
    "auto-risk-ad-consent": "Medium",
}


@pytest.mark.asyncio
async def test_detects_all_seven_planted_findings():
    findings = await RuleBasedRiskDetector().detect(DEMO_DOCS)
    by_id = {f.risk_id: f for f in findings}

    assert set(by_id) == set(EXPECTED_IDS)
    for risk_id, severity in EXPECTED_IDS.items():
        assert by_id[risk_id].severity == severity


@pytest.mark.asyncio
async def test_contradictions_quote_both_documents():
    by_id = {f.risk_id: f for f in await RuleBasedRiskDetector().detect(DEMO_DOCS)}

    tick = by_id["auto-contradiction-tick-rate"]
    assert tick.kind == "contradiction"
    assert tick.a_file == "backend_architecture_overview.md" and "30 Hz" in tick.a_text
    assert tick.b_file == "server_fleet_runbook.pdf" and "60 Hz" in tick.b_text


@pytest.mark.asyncio
async def test_risks_carry_source_and_real_description():
    by_id = {f.risk_id: f for f in await RuleBasedRiskDetector().detect(DEMO_DOCS)}

    pii = by_id["auto-risk-pii-retention"]
    assert pii.kind == "risk"
    assert pii.source == "data_pipeline_spec.pdf"
    assert "purge window" in pii.description.lower()
    assert not pii.description.lower().startswith("open gap")  # lead-in stripped


@pytest.mark.asyncio
async def test_missing_documents_yield_no_false_findings():
    findings = await RuleBasedRiskDetector().detect([_doc("unrelated.txt", "nothing here.")])
    assert findings == []


@pytest.mark.asyncio
async def test_ids_are_deterministic_across_runs():
    first = {f.risk_id for f in await RuleBasedRiskDetector().detect(DEMO_DOCS)}
    second = {f.risk_id for f in await RuleBasedRiskDetector().detect(DEMO_DOCS)}
    assert first == second == set(EXPECTED_IDS)
