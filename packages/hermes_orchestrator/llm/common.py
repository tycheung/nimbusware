"""LLM-backed plan stage: two critics + gate JSON ."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, Field, ValidationError

from agent_core.models import (
    CriticVerdictEmittedEvent,
    CriticVerdictEmittedPayload,
    EventType,
    GateDecisionEmittedEvent,
    GateDecisionEmittedPayload,
    RequiredFixArtifact,
    Severity,
    StageStartedEvent,
    StageStartedPayload,
    Verdict,
)
from hermes_extensions.phase2 import UniversalCritiqueRouter
from hermes_orchestrator.ollama_chat import ollama_chat_json
from hermes_orchestrator.registry import RoleRegistry
from hermes_orchestrator.unanimous_gate import gate_decision_from_critic_verdicts
from hermes_store.protocol import EventStore


class LlmCriticLine(BaseModel):
    model_config = {"extra": "ignore"}

    tax_key: str = Field(min_length=1)
    verdict: str = "PASS"
    severity: str = "LOW"
    is_in_domain: bool = True
    evidence_refs: list[str] | None = None
    required_fixes: list[dict[str, Any]] = Field(default_factory=list)


class LlmGateLine(BaseModel):
    model_config = {"extra": "ignore"}

    verdict: str = "PASS"


class LlmPlanResponse(BaseModel):
    model_config = {"extra": "ignore"}

    critics: list[LlmCriticLine] = Field(min_length=2)
    gate: LlmGateLine


IMPLEMENTATION_CRITIQUE_STAGE = "implementation.critique"
TEST_WRITER_CRITIQUE_STAGE = "test_writer.critique"
PLANNER_CRITIQUE_STAGE = "planner.critique"
FRONTEND_WRITER_CRITIQUE_STAGE = "frontend_writer.critique"
MODULE_INTEGRATOR_CRITIQUE_STAGE = "module_integrator.critique"
SELF_REFINEMENT_CRITIQUE_STAGE = "self_refinement.critique"


def append_gate_decision_event(
    store: EventStore,
    *,
    run_id: UUID,
    payload: GateDecisionEmittedPayload,
    extra_metadata: dict[str, Any] | None = None,
) -> None:
    """Append gate decision with stage-graph + live critic-matrix metadata when available."""
    from hermes_orchestrator.critic_matrix_live import enrich_gate_metadata_with_critic_matrix_live
    from hermes_orchestrator.stage_graph import (
        event_metadata_for_stage,
        stage_graph_from_run_created_metadata,
    )

    rows = store.list_run_events(str(run_id))
    sg_snapshot: dict[str, Any] | None = None
    for row in rows:
        if row.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = row.get("metadata")
        if isinstance(meta, dict):
            sg_snapshot = stage_graph_from_run_created_metadata(meta)
        break
    stage_meta = event_metadata_for_stage(sg_snapshot, payload.stage_name)
    merged = {**stage_meta, **(extra_metadata or {})}
    gate_meta = enrich_gate_metadata_with_critic_matrix_live(
        rows,
        stage_name=payload.stage_name,
        base_metadata=merged,
    )
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata=gate_meta,
            payload=payload,
        ),
    )


def _unanimous_gate_enforce_for_run(store: EventStore, run_id: UUID) -> bool:
    import os
    from pathlib import Path

    from hermes_orchestrator.integrator_gate import workflow_profile_from_run_created_rows
    from hermes_orchestrator.workflow_universal_critique import effective_universal_critique

    rows = store.list_run_events(str(run_id))
    for row in rows:
        if row.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            break
        frozen = meta.get("universal_critique_effective")
        if isinstance(frozen, dict):
            val = frozen.get("unanimous_gate_enforce")
            if isinstance(val, bool):
                return val
        break
    repo = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    wf = workflow_profile_from_run_created_rows(rows)
    return effective_universal_critique(repo, wf).unanimous_gate_enforce


def _finalize_critique_gate(
    store: EventStore,
    *,
    run_id: UUID,
    stage_name: str,
    critic_payloads: list[CriticVerdictEmittedPayload],
    enforce: bool | None = None,
    llm_fallback_verdict: Verdict | None = None,
    failure_reason_code: str | None = None,
) -> None:
    if enforce is None:
        enforce = _unanimous_gate_enforce_for_run(store, run_id)
    gate = gate_decision_from_critic_verdicts(
        critic_payloads,
        stage_name=stage_name,
        unanimous_pass_required=True,
        enforce=enforce,
        llm_fallback_verdict=llm_fallback_verdict,
        failure_reason_code=failure_reason_code,
    )
    append_gate_decision_event(store, run_id=run_id, payload=gate)


class LlmSelfRefinementCritiqueResponse(BaseModel):
    model_config = {"extra": "ignore"}

    verdict: str = "FAIL"
    gate_decision: str = "hold"
    summary: str = ""


class LlmAgentEvaluatorPolicyResponse(BaseModel):
    model_config = {"extra": "ignore"}

    status: str = "ok"
    gaps: list[str] = Field(default_factory=list)
    summary: str = ""


def _parse_verdict(raw: str) -> Verdict:
    return Verdict(str(raw).strip().upper())


def _parse_severity(raw: str) -> Severity:
    return Severity(str(raw).strip().upper())


def _fixes_from_llm(raw: object) -> list[RequiredFixArtifact]:
    if not isinstance(raw, list) or not raw:
        return []
    out: list[RequiredFixArtifact] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(RequiredFixArtifact.model_validate(item))
    return out


__all__ = [name for name in globals() if not name.startswith("__")]
