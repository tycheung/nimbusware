from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from agent_core.models import CriticVerdictEmittedPayload, GateDecisionEmittedPayload, Verdict


def _role_id_from_raw(raw: object) -> UUID | None:
    if isinstance(raw, UUID):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return UUID(raw.strip())
        except ValueError:
            return None
    return None


def gate_decision_from_critic_verdicts(
    verdicts: Sequence[CriticVerdictEmittedPayload],
    *,
    stage_name: str,
    unanimous_pass_required: bool = True,
    enforce: bool = False,
    llm_fallback_verdict: Verdict | None = None,
    failure_reason_code: str | None = None,
) -> GateDecisionEmittedPayload:
    if not enforce:
        return GateDecisionEmittedPayload(
            stage_name=stage_name,
            verdict=Verdict.PASS,
            unanimous_pass_required=unanimous_pass_required,
        )

    failing_critics: list[UUID] = []
    for payload in verdicts:
        if not payload.is_in_domain:
            continue
        if payload.verdict == Verdict.FAIL:
            failing_critics.append(payload.critic_role)

    if failing_critics:
        return GateDecisionEmittedPayload(
            stage_name=stage_name,
            verdict=Verdict.FAIL,
            unanimous_pass_required=unanimous_pass_required,
            failing_critics=failing_critics,
        )

    if llm_fallback_verdict == Verdict.FAIL:
        code = (failure_reason_code or "llm_gate_fail").strip() or "llm_gate_fail"
        return GateDecisionEmittedPayload(
            stage_name=stage_name,
            verdict=Verdict.FAIL,
            unanimous_pass_required=unanimous_pass_required,
            failure_reason_code=code,
        )

    return GateDecisionEmittedPayload(
        stage_name=stage_name,
        verdict=Verdict.PASS,
        unanimous_pass_required=unanimous_pass_required,
    )


def critic_verdict_payloads_for_stage(
    events: list[dict[str, Any]],
    stage_name: str,
) -> list[CriticVerdictEmittedPayload]:
    """Collect critic verdict payloads after the latest ``stage.started`` for a stage."""
    start_idx = -1
    for idx, ev in enumerate(events):
        if ev.get("event_type") != "stage.started":
            continue
        pl = ev.get("payload")
        if not isinstance(pl, dict):
            continue
        sn = pl.get("stage_name")
        if sn == stage_name:
            start_idx = idx

    if start_idx < 0:
        return []

    out: list[CriticVerdictEmittedPayload] = []
    for ev in events[start_idx + 1 :]:
        if ev.get("event_type") == "gate.decision.emitted":
            pl = ev.get("payload")
            if isinstance(pl, dict) and pl.get("stage_name") == stage_name:
                break
        if ev.get("event_type") != "critic.verdict.emitted":
            continue
        pl = ev.get("payload")
        if not isinstance(pl, dict):
            continue
        try:
            out.append(CriticVerdictEmittedPayload.model_validate(pl))
        except ValidationError:
            continue
    return out


def recompute_gate_for_stage(
    events: list[dict[str, Any]],
    stage_name: str,
    *,
    unanimous_pass_required: bool = True,
    enforce: bool = True,
) -> dict[str, Any]:
    """Live matrix helper: recompute gate payload dict from stored critic rows."""
    payloads = critic_verdict_payloads_for_stage(events, stage_name)
    gate = gate_decision_from_critic_verdicts(
        payloads,
        stage_name=stage_name,
        unanimous_pass_required=unanimous_pass_required,
        enforce=enforce,
    )
    row: dict[str, Any] = {
        "stage_name": gate.stage_name,
        "verdict": gate.verdict.value,
        "unanimous_pass_required": gate.unanimous_pass_required,
    }
    if gate.failing_critics:
        row["failing_critics"] = [str(r) for r in gate.failing_critics]
    if gate.failure_reason_code:
        row["failure_reason_code"] = gate.failure_reason_code
    return row


def failing_critics_from_gate_payload(payload: Mapping[str, Any]) -> list[str]:
    raw = payload.get("failing_critics")
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        rid = _role_id_from_raw(item)
        out.append(str(rid) if rid is not None else str(item))
    return out
