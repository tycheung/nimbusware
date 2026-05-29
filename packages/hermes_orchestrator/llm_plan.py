"""LLM-backed plan stage: two critics + gate JSON (plan §12 Phase 1)."""

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
    repo = Path(os.environ.get("HERMES_REPO_ROOT", ".")).resolve()
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


def emit_stub_plan_stage(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
) -> None:
    """Deterministic PASS plan stage (same semantics as MVP stub in ``pipeline``)."""
    planner = registry.resolve("planner")
    critic_roles = [
        registry.resolve(tax_key) for tax_key in critique_router.pairing_for("planner")
    ]
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name="plan", attempt=1),
        ),
    )
    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for critic_role in critic_roles:
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=Verdict.PASS,
            severity=Severity.LOW,
            owner_role=planner,
            is_in_domain=True,
            evidence_refs=["stub://mvp"],
        )
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
        critic_payloads.append(payload)
    _finalize_critique_gate(
        store,
        run_id=run_id,
        stage_name="plan",
        critic_payloads=critic_payloads,
    )


def emit_stub_implementation_critique_panel(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
) -> None:
    """PASS critic + gate events for ``backend_writer`` (§14 #16 beyond **plan**).

    Paired critics come from ``critique_pairings.yaml``. Caller must gate on
    ``HERMES_STUB_IMPLEMENTATION_CRITICS`` (or equivalent) so default runs stay
    unchanged.
    """
    owner = registry.resolve("backend_writer")
    tax_keys = critique_router.pairing_for("backend_writer")
    if len(tax_keys) < 2:
        return
    stage_name = IMPLEMENTATION_CRITIQUE_STAGE
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=Verdict.PASS,
            severity=Severity.LOW,
            owner_role=owner,
            is_in_domain=True,
            evidence_refs=["stub://implementation"],
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
    _finalize_critique_gate(
        store,
        run_id=run_id,
        stage_name=stage_name,
        critic_payloads=critic_payloads,
    )


def execute_plan_stage_llm(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    base_url: str,
    model_id: str,
    timeout_seconds: float = 120.0,
) -> None:
    planner = registry.resolve("planner")
    plan_critics = critique_router.pairing_for("planner")
    if len(plan_critics) < 2:
        emit_stub_plan_stage(store, registry, critique_router, run_id=run_id)
        return
    tax_key_union = "|".join(f'"{k}"' for k in plan_critics)
    system = (
        "You are a Hermes orchestration helper. Reply with JSON only. "
        f'Schema: {{"critics":[{{"tax_key":{tax_key_union},'
        '"verdict":"PASS"|"FAIL","severity":"LOW"|"MEDIUM"|"HIGH"|"BLOCKER",'
        '"is_in_domain":true|false,"evidence_refs":["string"],'
        '"required_fixes":[]}],"gate":{"verdict":"PASS"|"FAIL"}}. '
        "For FAIL verdict each critic must include non-empty required_fixes with "
        "artifact_schema_version=1, format=json_patch, target_files, patch_artifact, "
        "validation_steps, acceptance_criteria. Prefer PASS for a generic plan."
    )
    user = "Evaluate the plan stage for a generic software delivery plan."
    try:
        data = ollama_chat_json(
            base_url=base_url,
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout_seconds=timeout_seconds,
        )
        plan = LlmPlanResponse.model_validate(data)
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
    ):
        emit_stub_plan_stage(store, registry, critique_router, run_id=run_id)
        return

    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name="plan", attempt=1),
        ),
    )
    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for c in plan.critics:
        key = c.tax_key.strip().lower()
        critic_role = registry.resolve(key)
        verdict = _parse_verdict(c.verdict)
        severity = _parse_severity(c.severity)
        evidence_refs = list(c.evidence_refs) if c.evidence_refs else []
        fixes = _fixes_from_llm(c.required_fixes)
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=severity,
            owner_role=planner,
            is_in_domain=c.is_in_domain,
            evidence_refs=evidence_refs or ["llm://plan"],
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
    gv = _parse_verdict(plan.gate.verdict)
    _finalize_critique_gate(
        store,
        run_id=run_id,
        stage_name="plan",
        critic_payloads=critic_payloads,
        llm_fallback_verdict=gv,
        failure_reason_code="llm_gate_fail" if gv == Verdict.FAIL else None,
    )


def execute_implementation_critique_llm(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    base_url: str,
    model_id: str,
    verifier_exit_code: int,
    log_snippet: str,
    timeout_seconds: float = 120.0,
) -> bool:
    """LLM-backed **implementation.critique** panel for ``backend_writer`` (§14 #16).

    Returns ``True`` if critic + gate events were appended; ``False`` on any
    failure (caller may fall back to :func:`emit_stub_implementation_critique_panel`).

    Gating (``HERMES_IMPLEMENTATION_CRITIQUE_LLM`` + stub fallback) lives in
    :meth:`hermes_orchestrator.pipeline.RunOrchestrator.execute_writer_verifier_pass`.
    """
    owner = registry.resolve("backend_writer")
    tax_keys = critique_router.pairing_for("backend_writer")
    if len(tax_keys) < 2:
        return False
    tax_key_union = "|".join(f'"{k}"' for k in tax_keys)
    system = (
        "You are a Hermes orchestration helper. Reply with JSON only. "
        f'Schema: {{"critics":[{{"tax_key":{tax_key_union},'
        '"verdict":"PASS"|"FAIL","severity":"LOW"|"MEDIUM"|"HIGH"|"BLOCKER",'
        '"is_in_domain":true|false,"evidence_refs":["string"],'
        '"required_fixes":[]}],"gate":{"verdict":"PASS"|"FAIL"}}. '
        "For FAIL verdict each critic must include non-empty required_fixes with "
        "artifact_schema_version=1, format=json_patch, target_files, patch_artifact, "
        "validation_steps, acceptance_criteria. Prefer PASS when the log looks healthy."
    )
    bounded = (log_snippet or "")[:4000]
    user = (
        f"Verifier exit_code={verifier_exit_code}. "
        f"Last lines of verifier log (truncated):\n{bounded}"
    )
    try:
        data = ollama_chat_json(
            base_url=base_url,
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout_seconds=timeout_seconds,
        )
        parsed = LlmPlanResponse.model_validate(data)
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
    ):
        return False

    stage_name = IMPLEMENTATION_CRITIQUE_STAGE
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for c in parsed.critics:
        key = c.tax_key.strip().lower()
        critic_role = registry.resolve(key)
        verdict = _parse_verdict(c.verdict)
        severity = _parse_severity(c.severity)
        evidence_refs = list(c.evidence_refs) if c.evidence_refs else []
        fixes = _fixes_from_llm(c.required_fixes)
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=severity,
            owner_role=owner,
            is_in_domain=c.is_in_domain,
            evidence_refs=evidence_refs or ["llm://implementation"],
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
    gv = _parse_verdict(parsed.gate.verdict)
    _finalize_critique_gate(
        store,
        run_id=run_id,
        stage_name=stage_name,
        critic_payloads=critic_payloads,
        llm_fallback_verdict=gv,
        failure_reason_code="llm_gate_fail" if gv == Verdict.FAIL else None,
    )
    return True


def emit_stub_test_writer_critique_panel(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
) -> None:
    """PASS critic + gate events for ``test_writer`` (§14 #16).

    Paired critics come from ``critique_pairings.yaml``. Caller must gate on
    ``HERMES_ENABLE_TEST_WRITER_CRITIQUE`` and ``HERMES_STUB_TEST_WRITER_CRITICS``
    so default runs stay unchanged.
    """
    owner = registry.resolve("test_writer")
    tax_keys = critique_router.pairing_for("test_writer")
    if len(tax_keys) < 2:
        return
    stage_name = TEST_WRITER_CRITIQUE_STAGE
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=Verdict.PASS,
            severity=Severity.LOW,
            owner_role=owner,
            is_in_domain=True,
            evidence_refs=["stub://test_writer"],
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
    _finalize_critique_gate(
        store,
        run_id=run_id,
        stage_name=stage_name,
        critic_payloads=critic_payloads,
    )


def execute_test_writer_critique_llm(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    base_url: str,
    model_id: str,
    verifier_exit_code: int,
    log_snippet: str,
    timeout_seconds: float = 120.0,
) -> bool:
    """LLM-backed **test_writer.critique** panel (§14 #16).

    Returns ``True`` if critic + gate events were appended; ``False`` on any
    failure (caller may fall back to :func:`emit_stub_test_writer_critique_panel`).
    """
    owner = registry.resolve("test_writer")
    tax_keys = critique_router.pairing_for("test_writer")
    if len(tax_keys) < 2:
        return False
    tax_key_union = "|".join(f'"{k}"' for k in tax_keys)
    system = (
        "You are a Hermes orchestration helper. Reply with JSON only. "
        f'Schema: {{"critics":[{{"tax_key":{tax_key_union},'
        '"verdict":"PASS"|"FAIL","severity":"LOW"|"MEDIUM"|"HIGH"|"BLOCKER",'
        '"is_in_domain":true|false,"evidence_refs":["string"],'
        '"required_fixes":[]}],"gate":{"verdict":"PASS"|"FAIL"}}. '
        "For FAIL verdict each critic must include non-empty required_fixes with "
        "artifact_schema_version=1, format=json_patch, target_files, patch_artifact, "
        "validation_steps, acceptance_criteria. Prefer PASS when the log looks healthy."
    )
    bounded = (log_snippet or "")[:4000]
    user = (
        f"Verifier exit_code={verifier_exit_code}. "
        f"Last lines of verifier log (truncated):\n{bounded}"
    )
    try:
        data = ollama_chat_json(
            base_url=base_url,
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout_seconds=timeout_seconds,
        )
        parsed = LlmPlanResponse.model_validate(data)
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
    ):
        return False

    stage_name = TEST_WRITER_CRITIQUE_STAGE
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for c in parsed.critics:
        key = c.tax_key.strip().lower()
        critic_role = registry.resolve(key)
        verdict = _parse_verdict(c.verdict)
        severity = _parse_severity(c.severity)
        evidence_refs = list(c.evidence_refs) if c.evidence_refs else []
        fixes = _fixes_from_llm(c.required_fixes)
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=severity,
            owner_role=owner,
            is_in_domain=c.is_in_domain,
            evidence_refs=evidence_refs or ["llm://test_writer"],
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
    gv = _parse_verdict(parsed.gate.verdict)
    _finalize_critique_gate(
        store,
        run_id=run_id,
        stage_name=stage_name,
        critic_payloads=critic_payloads,
        llm_fallback_verdict=gv,
        failure_reason_code="llm_gate_fail" if gv == Verdict.FAIL else None,
    )
    return True


def emit_stub_planner_critique_panel(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
) -> None:
    """PASS critic + gate events for ``planner`` post-verify review (§14 #16).

    Paired critics come from ``critique_pairings.yaml``. Caller must gate on
    ``HERMES_ENABLE_PLANNER_CRITIQUE`` and ``HERMES_STUB_PLANNER_CRITICS``.
    """
    owner = registry.resolve("planner")
    tax_keys = critique_router.pairing_for("planner")
    if len(tax_keys) < 2:
        return
    stage_name = PLANNER_CRITIQUE_STAGE
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=Verdict.PASS,
            severity=Severity.LOW,
            owner_role=owner,
            is_in_domain=True,
            evidence_refs=["stub://planner"],
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
    _finalize_critique_gate(
        store,
        run_id=run_id,
        stage_name=stage_name,
        critic_payloads=critic_payloads,
    )


def execute_planner_critique_llm(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    base_url: str,
    model_id: str,
    verifier_exit_code: int,
    log_snippet: str,
    timeout_seconds: float = 120.0,
) -> bool:
    """LLM-backed **planner.critique** panel after verify (§14 #16).

    Returns ``True`` if critic + gate events were appended; ``False`` on any
    failure (caller may fall back to :func:`emit_stub_planner_critique_panel`).
    """
    owner = registry.resolve("planner")
    tax_keys = critique_router.pairing_for("planner")
    if len(tax_keys) < 2:
        return False
    tax_key_union = "|".join(f'"{k}"' for k in tax_keys)
    system = (
        "You are a Hermes orchestration helper. Reply with JSON only. "
        f'Schema: {{"critics":[{{"tax_key":{tax_key_union},'
        '"verdict":"PASS"|"FAIL","severity":"LOW"|"MEDIUM"|"HIGH"|"BLOCKER",'
        '"is_in_domain":true|false,"evidence_refs":["string"],'
        '"required_fixes":[]}],"gate":{"verdict":"PASS"|"FAIL"}}. '
        "For FAIL verdict each critic must include non-empty required_fixes with "
        "artifact_schema_version=1, format=json_patch, target_files, patch_artifact, "
        "validation_steps, acceptance_criteria. Prefer PASS when the log looks healthy."
    )
    bounded = (log_snippet or "")[:4000]
    user = (
        f"Post-verify planner review. Verifier exit_code={verifier_exit_code}. "
        f"Last lines of verifier log (truncated):\n{bounded}"
    )
    try:
        data = ollama_chat_json(
            base_url=base_url,
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout_seconds=timeout_seconds,
        )
        parsed = LlmPlanResponse.model_validate(data)
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
    ):
        return False

    stage_name = PLANNER_CRITIQUE_STAGE
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for c in parsed.critics:
        key = c.tax_key.strip().lower()
        critic_role = registry.resolve(key)
        verdict = _parse_verdict(c.verdict)
        severity = _parse_severity(c.severity)
        evidence_refs = list(c.evidence_refs) if c.evidence_refs else []
        fixes = _fixes_from_llm(c.required_fixes)
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=severity,
            owner_role=owner,
            is_in_domain=c.is_in_domain,
            evidence_refs=evidence_refs or ["llm://planner"],
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
    gv = _parse_verdict(parsed.gate.verdict)
    _finalize_critique_gate(
        store,
        run_id=run_id,
        stage_name=stage_name,
        critic_payloads=critic_payloads,
        llm_fallback_verdict=gv,
        failure_reason_code="llm_gate_fail" if gv == Verdict.FAIL else None,
    )
    return True


def emit_stub_frontend_writer_critique_panel(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
) -> None:
    owner = registry.resolve("frontend_writer")
    tax_keys = critique_router.pairing_for("frontend_writer")
    if len(tax_keys) < 2:
        return
    stage_name = FRONTEND_WRITER_CRITIQUE_STAGE
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=Verdict.PASS,
            severity=Severity.LOW,
            owner_role=owner,
            is_in_domain=True,
            evidence_refs=["stub://frontend_writer"],
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
    _finalize_critique_gate(
        store,
        run_id=run_id,
        stage_name=stage_name,
        critic_payloads=critic_payloads,
    )


def execute_frontend_writer_critique_llm(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    base_url: str,
    model_id: str,
    verifier_exit_code: int,
    log_snippet: str,
    timeout_seconds: float = 120.0,
) -> bool:
    owner = registry.resolve("frontend_writer")
    tax_keys = critique_router.pairing_for("frontend_writer")
    if len(tax_keys) < 2:
        return False
    tax_key_union = "|".join(f'"{k}"' for k in tax_keys)
    system = (
        "You are a Hermes orchestration helper. Reply with JSON only. "
        f'Schema: {{"critics":[{{"tax_key":{tax_key_union},'
        '"verdict":"PASS"|"FAIL","severity":"LOW"|"MEDIUM"|"HIGH"|"BLOCKER",'
        '"is_in_domain":true|false,"evidence_refs":["string"],'
        '"required_fixes":[]}],"gate":{"verdict":"PASS"|"FAIL"}}. '
        "For FAIL verdict each critic must include non-empty required_fixes with "
        "artifact_schema_version=1, format=json_patch, target_files, patch_artifact, "
        "validation_steps, acceptance_criteria. Prefer PASS when the log looks healthy."
    )
    bounded = (log_snippet or "")[:4000]
    user = (
        f"Post-verify frontend writer review. Verifier exit_code={verifier_exit_code}. "
        f"Last lines of verifier log (truncated):\n{bounded}"
    )
    try:
        data = ollama_chat_json(
            base_url=base_url,
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout_seconds=timeout_seconds,
        )
        parsed = LlmPlanResponse.model_validate(data)
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
    ):
        return False
    stage_name = FRONTEND_WRITER_CRITIQUE_STAGE
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for c in parsed.critics:
        key = c.tax_key.strip().lower()
        critic_role = registry.resolve(key)
        verdict = _parse_verdict(c.verdict)
        severity = _parse_severity(c.severity)
        evidence_refs = list(c.evidence_refs) if c.evidence_refs else []
        fixes = _fixes_from_llm(c.required_fixes)
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=severity,
            owner_role=owner,
            is_in_domain=c.is_in_domain,
            evidence_refs=evidence_refs or ["llm://frontend_writer"],
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
    gv = _parse_verdict(parsed.gate.verdict)
    _finalize_critique_gate(
        store,
        run_id=run_id,
        stage_name=stage_name,
        critic_payloads=critic_payloads,
        llm_fallback_verdict=gv,
        failure_reason_code="llm_gate_fail" if gv == Verdict.FAIL else None,
    )
    return True


def emit_stub_module_integrator_critique_panel(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
) -> None:
    owner = registry.resolve("module_integrator")
    tax_keys = critique_router.pairing_for("module_integrator")
    if len(tax_keys) < 2:
        return
    stage_name = MODULE_INTEGRATOR_CRITIQUE_STAGE
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=Verdict.PASS,
            severity=Severity.LOW,
            owner_role=owner,
            is_in_domain=True,
            evidence_refs=["stub://module_integrator"],
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
    _finalize_critique_gate(
        store,
        run_id=run_id,
        stage_name=stage_name,
        critic_payloads=critic_payloads,
    )


def execute_module_integrator_critique_llm(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    base_url: str,
    model_id: str,
    verifier_exit_code: int,
    log_snippet: str,
    timeout_seconds: float = 120.0,
) -> bool:
    owner = registry.resolve("module_integrator")
    tax_keys = critique_router.pairing_for("module_integrator")
    if len(tax_keys) < 2:
        return False
    tax_key_union = "|".join(f'"{k}"' for k in tax_keys)
    system = (
        "You are a Hermes orchestration helper. Reply with JSON only. "
        f'Schema: {{"critics":[{{"tax_key":{tax_key_union},'
        '"verdict":"PASS"|"FAIL","severity":"LOW"|"MEDIUM"|"HIGH"|"BLOCKER",'
        '"is_in_domain":true|false,"evidence_refs":["string"],'
        '"required_fixes":[]}],"gate":{"verdict":"PASS"|"FAIL"}}. '
        "For FAIL verdict each critic must include non-empty required_fixes with "
        "artifact_schema_version=1, format=json_patch, target_files, patch_artifact, "
        "validation_steps, acceptance_criteria. Prefer PASS when the log looks healthy."
    )
    bounded = (log_snippet or "")[:4000]
    user = (
        f"Post-verify module integrator review. Verifier exit_code={verifier_exit_code}. "
        f"Last lines of verifier log (truncated):\n{bounded}"
    )
    try:
        data = ollama_chat_json(
            base_url=base_url,
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout_seconds=timeout_seconds,
        )
        parsed = LlmPlanResponse.model_validate(data)
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
    ):
        return False
    stage_name = MODULE_INTEGRATOR_CRITIQUE_STAGE
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for c in parsed.critics:
        key = c.tax_key.strip().lower()
        critic_role = registry.resolve(key)
        verdict = _parse_verdict(c.verdict)
        severity = _parse_severity(c.severity)
        evidence_refs = list(c.evidence_refs) if c.evidence_refs else []
        fixes = _fixes_from_llm(c.required_fixes)
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=severity,
            owner_role=owner,
            is_in_domain=c.is_in_domain,
            evidence_refs=evidence_refs or ["llm://module_integrator"],
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
    gv = _parse_verdict(parsed.gate.verdict)
    _finalize_critique_gate(
        store,
        run_id=run_id,
        stage_name=stage_name,
        critic_payloads=critic_payloads,
        llm_fallback_verdict=gv,
        failure_reason_code="llm_gate_fail" if gv == Verdict.FAIL else None,
    )
    return True


def emit_stub_self_refinement_critique_panel(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
) -> None:
    """PASS critic + gate events for self-refinement Phase D (section 14 item 17)."""
    owner = registry.resolve("planner")
    tax_keys = critique_router.pairing_for("planner")
    if len(tax_keys) < 1:
        return
    stage_name = SELF_REFINEMENT_CRITIQUE_STAGE
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for tax_key in tax_keys[:2]:
        critic_role = registry.resolve(tax_key)
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=Verdict.PASS,
            severity=Severity.LOW,
            owner_role=owner,
            is_in_domain=True,
            evidence_refs=["stub://self_refinement"],
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
    _finalize_critique_gate(
        store,
        run_id=run_id,
        stage_name=stage_name,
        critic_payloads=critic_payloads,
    )


def execute_self_refinement_critique_llm(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    base_url: str,
    model_id: str,
    evaluation_status: str | None,
    gaps: list[str],
    description: str,
    timeout_seconds: float = 120.0,
) -> dict[str, str] | None:
    """LLM-backed self-refinement critique panel + Phase D branch metadata.

    Appends ``self_refinement.critique`` stage/critic/gate events when Ollama returns
    valid JSON. Returns branch dict for loop signal enrichment; ``None`` on failure.
    """
    owner = registry.resolve("planner")
    tax_keys = critique_router.pairing_for("planner")
    if len(tax_keys) < 1:
        return None
    system = (
        "You are a Hermes self-refinement orchestration helper. Reply with JSON only. "
        'Schema: {"verdict":"PASS"|"FAIL","gate_decision":"proceed"|"hold",'
        '"summary":"string"}. Recommend proceed only when gaps are minor or the '
        "policy description indicates readiness; otherwise hold."
    )
    bounded_desc = (description or "")[:2000]
    user = (
        f"evaluation_status={evaluation_status!r}. gaps={list(gaps)!r}. "
        f"policy_description={bounded_desc!r}"
    )
    try:
        data = ollama_chat_json(
            base_url=base_url,
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout_seconds=timeout_seconds,
        )
        parsed = LlmSelfRefinementCritiqueResponse.model_validate(data)
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
    ):
        return None
    verdict = _parse_verdict(parsed.verdict)
    gate_raw = str(parsed.gate_decision).strip().lower()
    gate = "proceed" if gate_raw == "proceed" else "hold"
    summary = str(parsed.summary or "").strip()[:500]
    stage_name = SELF_REFINEMENT_CRITIQUE_STAGE
    severity = Severity.MEDIUM if verdict == Verdict.FAIL else Severity.LOW
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    critic_role = registry.resolve(tax_keys[0])
    store.append(
        CriticVerdictEmittedEvent(
            event_type=EventType.CRITIC_VERDICT_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            actor_role=critic_role,
            payload=CriticVerdictEmittedPayload(
                critic_role=critic_role,
                verdict=verdict,
                severity=severity,
                owner_role=owner,
                is_in_domain=True,
                evidence_refs=[f"llm://self_refinement:{summary[:120]}"],
            ),
        ),
    )
    gate_verdict = Verdict.PASS if gate == "proceed" else Verdict.FAIL
    gate_payload: dict[str, Any] = {
        "stage_name": stage_name,
        "verdict": gate_verdict,
        "unanimous_pass_required": True,
    }
    if gate_verdict == Verdict.FAIL:
        gate_payload["failure_reason_code"] = "llm_self_refinement_gate_hold"
    append_gate_decision_event(
        store,
        run_id=run_id,
        payload=GateDecisionEmittedPayload.model_validate(gate_payload),
    )
    return {
        "verdict": verdict.value,
        "gate_decision": gate,
        "summary": summary,
    }


def execute_agent_evaluator_policy_llm(
    store: EventStore,
    registry: RoleRegistry,
    *,
    run_id: UUID,
    base_url: str,
    model_id: str,
    rules_eval: dict[str, Any],
    persona_id: str,
    timeout_seconds: float = 120.0,
) -> dict[str, Any] | None:
    """Optional LLM policy branch for agent evaluator (metadata only; no new event types).

    Rules ``evaluate()`` remains authoritative for timeline status fields. Returns a dict
    with ``status``, ``gaps``, and ``summary`` for pipeline metadata enrichment.
    """
    _ = store, registry, run_id
    pid = str(persona_id).strip() or "default"
    rules_status = rules_eval.get("status")
    rules_gaps = rules_eval.get("gaps")
    gaps_list = [str(g) for g in rules_gaps] if isinstance(rules_gaps, list) else []
    system = (
        "You are a Hermes agent-evaluator policy helper. Reply with JSON only. "
        "Schema: status ok|needs_work|invalid, gaps string array, summary string. "
        "Complement rules evaluation; do not contradict obvious invalid shelf states."
    )
    user = (
        f"persona_id={pid!r}. rules_status={rules_status!r}. "
        f"rules_gaps={gaps_list!r}"
    )
    try:
        data = ollama_chat_json(
            base_url=base_url,
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout_seconds=timeout_seconds,
        )
        parsed = LlmAgentEvaluatorPolicyResponse.model_validate(data)
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
    ):
        return None
    status_raw = str(parsed.status).strip().lower()
    if status_raw in ("ok", "needs_work", "invalid"):
        status_out = status_raw
    else:
        status_out = "needs_work"
    gaps_out = [str(g).strip() for g in parsed.gaps if str(g).strip()][:20]
    summary = str(parsed.summary or "").strip()[:500]
    return {"status": status_out, "gaps": gaps_out, "summary": summary}
