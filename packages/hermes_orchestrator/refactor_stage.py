"""Refactorer producer + refactor critique panel."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import (
    CriticVerdictEmittedEvent,
    CriticVerdictEmittedPayload,
    EventType,
    RequiredFixArtifact,
    Severity,
    StagePassedEvent,
    StagePassedPayload,
    StageStartedEvent,
    StageStartedPayload,
    Verdict,
)
from hermes_extensions.phase2 import UniversalCritiqueRouter
from hermes_orchestrator.llm_plan import append_gate_decision_event
from hermes_orchestrator.registry import RoleRegistry
from hermes_orchestrator.unanimous_gate import gate_decision_from_critic_verdicts
from hermes_orchestrator.workflow_refactor import RefactorWorkflowBlock
from hermes_store.protocol import EventStore

REFACTOR_STAGE = "refactor"
REFACTOR_CRITIQUE_STAGE = "refactor.critique"
_REFACTOR_CRITIC = "refactor_critic"
_CODE_QUALITY_CRITIC = "code_quality_critic"

_REFACTOR_FAIL_FIX = RequiredFixArtifact.model_validate(
    {
        "artifact_schema_version": 1,
        "format": "json_patch",
        "target_files": ["packages/"],
        "patch_artifact": "[]",
        "validation_steps": ["address refactor critique findings"],
        "acceptance_criteria": "refactor.critique gate passes",
    },
)


def refactor_critique_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    last_gate: dict[str, Any] | None = None
    for row in events:
        if row.get("event_type") != "gate.decision.emitted":
            continue
        payload = row.get("payload") or {}
        if payload.get("stage_name") == REFACTOR_CRITIQUE_STAGE:
            last_gate = payload
    if last_gate is None:
        return None
    return {
        "stage_name": REFACTOR_CRITIQUE_STAGE,
        "verdict": last_gate.get("verdict"),
        "failing_critics": last_gate.get("failing_critics") or [],
    }


def emit_refactor_stage_and_critique(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    block: RefactorWorkflowBlock,
    unanimous_gate_enforce: bool = False,
    force_fail: bool = False,
) -> bool:
    """Rules-first refactor pass: stub proposal + paired critics + gate. Returns gate FAIL."""
    tax_keys = critique_router.pairing_for("refactorer")
    if len(tax_keys) < 2:
        return False
    owner = registry.resolve("refactorer")
    now = datetime.now(timezone.utc)

    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=now,
            metadata={
                "refactor": {
                    "stub_only": block.stub_only,
                    "max_iterations": block.max_iterations,
                },
            },
            payload=StageStartedPayload(stage_name=REFACTOR_STAGE, attempt=1),
        ),
    )
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"refactor": {"mode": "stub_proposal"}},
            payload=StagePassedPayload(stage_name=REFACTOR_STAGE, duration_ms=0),
        ),
    )

    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name=REFACTOR_CRITIQUE_STAGE, attempt=1),
        ),
    )

    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        fail = force_fail and tax_key in (_REFACTOR_CRITIC, _CODE_QUALITY_CRITIC)
        verdict = Verdict.FAIL if fail else Verdict.PASS
        fixes = [_REFACTOR_FAIL_FIX] if verdict == Verdict.FAIL else []
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=Severity.LOW if verdict == Verdict.PASS else Severity.MEDIUM,
            owner_role=owner,
            is_in_domain=True,
            evidence_refs=[f"refactor://{tax_key}"],
            required_fixes=fixes,
        )
        critic_payloads.append(payload)
        store.append(
            CriticVerdictEmittedEvent(
                event_type=EventType.CRITIC_VERDICT_EMITTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                actor_role=critic_role,
                payload=payload,
            ),
        )

    gate = gate_decision_from_critic_verdicts(
        critic_payloads,
        stage_name=REFACTOR_CRITIQUE_STAGE,
        unanimous_pass_required=True,
        enforce=unanimous_gate_enforce or force_fail,
    )
    append_gate_decision_event(store, run_id=run_id, payload=gate)
    return str(gate.verdict).upper() == "FAIL"
