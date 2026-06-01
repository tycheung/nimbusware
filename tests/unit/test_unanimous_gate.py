"""Deterministic unanimous gate engine ."""

from __future__ import annotations

from uuid import UUID

from agent_core.models import (
    CriticVerdictEmittedPayload,
    RequiredFixArtifact,
    Severity,
    Verdict,
)
from hermes_orchestrator.critic_matrix_live import (
    build_live_critic_matrix_rows,
    critic_matrix_unanimous_summary,
)
from hermes_orchestrator.unanimous_gate import (
    critic_verdict_payloads_for_stage,
    failing_critics_from_gate_payload,
    gate_decision_from_critic_verdicts,
    recompute_gate_for_stage,
)


def _payload(
    critic_id: str,
    *,
    verdict: Verdict,
    in_domain: bool = True,
) -> CriticVerdictEmittedPayload:
    rid = UUID(critic_id)
    fixes: list[RequiredFixArtifact] = []
    if verdict == Verdict.FAIL:
        fixes = [
            RequiredFixArtifact.model_validate(
                {
                    "artifact_schema_version": 1,
                    "format": "json_patch",
                    "target_files": ["README.md"],
                    "patch_artifact": "[]",
                    "validation_steps": ["review"],
                    "acceptance_criteria": "fixed",
                },
            ),
        ]
    return CriticVerdictEmittedPayload(
        critic_role=rid,
        verdict=verdict,
        severity=Severity.LOW,
        owner_role=rid,
        is_in_domain=in_domain,
        evidence_refs=["test://x"],
        required_fixes=fixes,
    )


def test_all_pass_critics_yield_pass_gate() -> None:
    gate = gate_decision_from_critic_verdicts(
        [
            _payload("22222222-2222-4222-8222-222222222202", verdict=Verdict.PASS),
            _payload("33333333-3333-4333-8333-333333333303", verdict=Verdict.PASS),
        ],
        stage_name="implementation.critique",
        enforce=True,
    )
    assert gate.verdict == Verdict.PASS


def test_one_fail_yields_fail_gate_with_failing_critics() -> None:
    gate = gate_decision_from_critic_verdicts(
        [
            _payload("22222222-2222-4222-8222-222222222202", verdict=Verdict.PASS),
            _payload("33333333-3333-4333-8333-333333333303", verdict=Verdict.FAIL),
        ],
        stage_name="implementation.critique",
        enforce=True,
    )
    assert gate.verdict == Verdict.FAIL
    assert len(gate.failing_critics) == 1


def test_out_of_domain_fail_ignored() -> None:
    gate = gate_decision_from_critic_verdicts(
        [
            _payload("22222222-2222-4222-8222-222222222202", verdict=Verdict.PASS),
            _payload(
                "33333333-3333-4333-8333-333333333303",
                verdict=Verdict.FAIL,
                in_domain=False,
            ),
        ],
        stage_name="implementation.critique",
        enforce=True,
    )
    assert gate.verdict == Verdict.PASS


def test_gate_skipped_when_enforce_false() -> None:
    gate = gate_decision_from_critic_verdicts([], stage_name="verify", enforce=False)
    assert gate.verdict == Verdict.PASS


def test_recompute_gate_for_stage_from_events() -> None:
    critic = _payload("22222222-2222-4222-8222-222222222202", verdict=Verdict.PASS)
    events = [
        {"event_type": "stage.started", "payload": {"stage_name": "verify"}},
        {"event_type": "critic.verdict.emitted", "payload": critic.model_dump(mode="json")},
    ]
    row = recompute_gate_for_stage(events, "verify", enforce=True)
    assert row["verdict"] == "PASS"


def test_failing_critics_from_gate_payload() -> None:
    rid = "22222222-2222-4222-8222-222222222202"
    out = failing_critics_from_gate_payload({"failing_critics": [rid]})
    assert out == [rid]


def test_critic_verdict_payloads_for_stage_empty_without_start() -> None:
    assert critic_verdict_payloads_for_stage([], "verify") == []


def test_live_matrix_summary_reflects_fail_stage() -> None:
    events = [
        {
            "event_type": "run.created",
            "metadata": {
                "stage_graph": {
                    "ordered_stage_names": ["implementation.critique"],
                    "nodes": [],
                    "parallel_groups": {},
                },
            },
        },
        {
            "event_type": "gate.decision.emitted",
            "payload": {
                "stage_name": "implementation.critique",
                "verdict": "FAIL",
                "unanimous_pass_required": True,
            },
        },
    ]
    rows = build_live_critic_matrix_rows(events)
    summary = critic_matrix_unanimous_summary(rows)
    assert summary["fail_count"] == 1
    assert "implementation.critique" in summary.get("fail_stage_names", [])
