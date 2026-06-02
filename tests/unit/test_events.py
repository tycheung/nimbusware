from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from agent_core.models import (
    EventType,
    FindingFixStrictnessSettings,
    NetworkEgressPolicySnapshot,
    PolicySnapshotV1,
    Severity,
    Verdict,
    finding_severity_requires_fixes,
    serialize_event_persistent,
    validate_event_dict,
)


def _rid() -> UUID:
    return uuid4()


def _fix() -> dict:
    return {
        "artifact_schema_version": 1,
        "format": "json_patch",
        "target_files": ["a.py"],
        "patch_artifact": "[]",
        "validation_steps": ["pytest"],
        "acceptance_criteria": "tests pass",
    }


def _envelope(event_type: str, payload: dict) -> dict:
    return {
        "event_type": event_type,
        "event_id": str(uuid4()),
        "run_id": str(uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }


def test_finding_strictness_high_floor_medium_no_fixes() -> None:
    """§4.2A edge: HIGH floor does not require fixes for MEDIUM (secondary LOW-only)."""
    settings = FindingFixStrictnessSettings(
        minimum_severity_requiring_fixes=Severity.HIGH,
        also_require_fixes_for_low_severity=True,
    )
    assert not finding_severity_requires_fixes(Severity.MEDIUM, settings)


def test_finding_created_requires_fixes_when_policy_says_so() -> None:
    rid = _rid()
    ctx = {"finding_fix_strictness": FindingFixStrictnessSettings()}
    payload = {
        "finding_id": str(uuid4()),
        "category": "bug",
        "owner_role": str(rid),
        "severity": Severity.HIGH.value,
        "source_artifact": "x",
        "repro_steps": [],
        "required_fixes": [_fix()],
    }
    ev = validate_event_dict(_envelope(EventType.FINDING_CREATED.value, payload), context=ctx)
    assert ev.payload.owner_role == rid


def test_finding_created_rejects_non_uuid_owner_role() -> None:
    ctx = {"finding_fix_strictness": FindingFixStrictnessSettings()}
    payload = {
        "finding_id": str(uuid4()),
        "category": "bug",
        "owner_role": "Frontend Writer",
        "severity": Severity.LOW.value,
        "source_artifact": "x",
        "repro_steps": [],
        "required_fixes": [],
    }
    with pytest.raises(ValidationError):
        validate_event_dict(_envelope(EventType.FINDING_CREATED.value, payload), context=ctx)


def test_validate_event_dict_wrong_payload_shape() -> None:
    rid = _rid()
    payload = {
        "finding_id": str(uuid4()),
        "category": "bug",
        "owner_role": str(rid),
        "severity": Severity.HIGH.value,
        "source_artifact": "x",
        "repro_steps": [],
        "required_fixes": [],
    }
    with pytest.raises(ValidationError):
        validate_event_dict(_envelope(EventType.FINDING_CREATED.value, payload))


def test_critic_pass_no_fixes() -> None:
    rid1, rid2 = _rid(), _rid()
    payload = {
        "critic_role": str(rid1),
        "verdict": Verdict.PASS.value,
        "severity": Severity.LOW.value,
        "owner_role": str(rid2),
        "is_in_domain": True,
        "evidence_refs": [],
        "finding_ids": [],
        "required_fixes": [],
    }
    validate_event_dict(_envelope(EventType.CRITIC_VERDICT_EMITTED.value, payload))


def test_critic_fail_requires_fixes() -> None:
    rid1, rid2 = _rid(), _rid()
    payload = {
        "critic_role": str(rid1),
        "verdict": Verdict.FAIL.value,
        "severity": Severity.HIGH.value,
        "owner_role": str(rid2),
        "is_in_domain": True,
        "evidence_refs": ["f.py"],
        "finding_ids": [],
        "required_fixes": [],
    }
    with pytest.raises(ValidationError):
        validate_event_dict(_envelope(EventType.CRITIC_VERDICT_EMITTED.value, payload))


def test_gate_fail_requires_signal() -> None:
    payload = {
        "stage_name": "plan",
        "verdict": Verdict.FAIL.value,
        "unanimous_pass_required": True,
        "failing_critics": [],
        "failing_finding_ids": [],
        "failure_reason_code": None,
    }
    with pytest.raises(ValidationError):
        validate_event_dict(_envelope(EventType.GATE_DECISION_EMITTED.value, payload))


def test_serialize_event_persistent_uuid_strings() -> None:
    rid = _rid()
    payload = {
        "critic_role": str(rid),
        "verdict": Verdict.PASS.value,
        "severity": Severity.LOW.value,
        "owner_role": str(rid),
        "is_in_domain": True,
        "evidence_refs": [],
        "finding_ids": [],
        "required_fixes": [],
    }
    ev = validate_event_dict(_envelope(EventType.CRITIC_VERDICT_EMITTED.value, payload))
    out = serialize_event_persistent(ev)
    assert out["payload"]["critic_role"] == str(rid)
    assert isinstance(out["payload"]["critic_role"], str)


def test_network_egress_rejects_negative_budget() -> None:
    with pytest.raises(ValidationError):
        NetworkEgressPolicySnapshot(budget_bytes_per_run=-1)


def test_policy_snapshot_on_run_created_optional() -> None:
    rid = _rid()
    snap = PolicySnapshotV1(
        finding_fix_strictness=FindingFixStrictnessSettings(),
        network_egress=NetworkEgressPolicySnapshot(
            scraper_role_allowlist=[rid],
            domain_allowlist=["example.org"],
            budget_bytes_per_run=100,
        ),
    )
    payload_min = {
        "workflow_profile": "default",
        "policy_version": "1",
        "config_snapshot_id": "cfg-1",
    }
    ev1 = validate_event_dict(_envelope(EventType.RUN_CREATED.value, payload_min))
    assert ev1.payload.policy_snapshot is None

    payload_full = {
        **payload_min,
        "policy_snapshot": snap.model_dump(mode="json"),
    }
    ev2 = validate_event_dict(_envelope(EventType.RUN_CREATED.value, payload_full))
    assert ev2.payload.policy_snapshot is not None
    assert ev2.payload.policy_snapshot.network_egress.scraper_role_allowlist == [rid]


def test_self_refinement_loop_signalled_event_shape() -> None:
    payload = {
        "phase": "D",
        "stage_name": "self_refinement:policy",
        "attempt": 1,
        "max_iterations": 3,
        "signal": "phase_d_kickoff",
    }
    ev = validate_event_dict(
        _envelope(EventType.SELF_REFINEMENT_LOOP_SIGNALLED.value, payload),
    )
    assert ev.payload.phase == "D"
    assert ev.payload.signal == "phase_d_kickoff"
    assert ev.payload.gate_decision == "hold"
    assert ev.payload.loops_remaining == 0
    assert ev.payload.orchestration_branch == "rules"
    assert ev.payload.llm_critique_enabled is False
    assert ev.payload.llm_critique_attempted is False


def test_self_refinement_loop_signalled_llm_branch_fields() -> None:
    payload = {
        "phase": "D",
        "stage_name": "self_refinement:policy",
        "attempt": 2,
        "max_iterations": 3,
        "signal": "phase_d_iteration",
        "gate_decision": "hold",
        "orchestration_branch": "rules_with_llm_critique",
        "llm_critique_enabled": True,
        "llm_critique_attempted": True,
        "llm_critique_verdict": "PASS",
        "llm_gate_decision": "proceed",
    }
    ev = validate_event_dict(
        _envelope(EventType.SELF_REFINEMENT_LOOP_SIGNALLED.value, payload),
    )
    assert ev.payload.orchestration_branch == "rules_with_llm_critique"
    assert ev.payload.llm_critique_verdict.value == "PASS"
    assert ev.payload.llm_gate_decision == "proceed"
