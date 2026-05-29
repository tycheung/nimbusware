"""Deterministic unanimous gate engine (plan §14 #16)."""

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
from hermes_orchestrator.unanimous_gate import gate_decision_from_critic_verdicts


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
