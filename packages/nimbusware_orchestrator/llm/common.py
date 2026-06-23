from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, Field, ValidationError

from agent_core.critique_stages import (
    FRONTEND_WRITER_CRITIQUE_STAGE,
    IMPLEMENTATION_CRITIQUE_STAGE,
    PLANNER_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
)
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
from nimbusware_env.env_flags import nimbusware_repo_root_path
from nimbusware_extensions.phase2 import UniversalCritiqueRouter
from nimbusware_orchestrator.ollama_chat import ollama_chat_json
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.unanimous_gate import gate_decision_from_critic_verdicts
from nimbusware_store.protocol import EventStore


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


MODULE_INTEGRATOR_CRITIQUE_STAGE = "module_integrator.critique"
SELF_REFINEMENT_CRITIQUE_STAGE = "self_refinement.critique"


def append_gate_decision_event(
    store: EventStore,
    *,
    run_id: UUID,
    payload: GateDecisionEmittedPayload,
    extra_metadata: dict[str, Any] | None = None,
) -> None:
    from agent_core.read.critic_matrix import enrich_gate_metadata_with_critic_matrix_live
    from agent_core.stage_graph import (
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

    from nimbusware_orchestrator.integrator_gate import workflow_profile_from_run_created_rows
    from nimbusware_orchestrator.workflow_universal_critique import effective_universal_critique

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
    repo = nimbusware_repo_root_path()
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


def emit_stub_role_critique_panel(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    producer_tax_key: str,
    stage_name: str,
    evidence_ref: str,
    min_pairing_count: int = 2,
    max_critics: int | None = None,
) -> None:
    owner = registry.resolve(producer_tax_key)
    tax_keys = critique_router.pairing_for(producer_tax_key)
    if len(tax_keys) < min_pairing_count:
        return
    if max_critics is not None:
        tax_keys = tax_keys[:max_critics]
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
            evidence_refs=[evidence_ref],
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


def ollama_chat_json_via_plan_patch(
    *,
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_seconds: float = 120.0,
    stage_name: str | None = None,
    agent_role: str | None = None,
) -> dict[str, Any]:
    role = (agent_role or "").strip() or None
    if not role and stage_name:
        from nimbusware_orchestrator.binding_preflight import agent_role_for_stage

        role = agent_role_for_stage(stage_name)
    if role:
        from nimbusware_env import find_repo_root
        from nimbusware_orchestrator.model_binding_resolver import ModelBindingResolver

        resolver = ModelBindingResolver(find_repo_root())
        return resolver.chat_json(
            role,
            messages=messages,
            timeout_seconds=timeout_seconds,
        )
    if stage_name:
        from nimbusware_config.persist import load_model_routing_dict
        from nimbusware_env import find_repo_root
        from nimbusware_orchestrator.stage_provider_routing import (
            cloud_chat_json,
            resolve_stage_provider,
        )

        routing = load_model_routing_dict(find_repo_root())
        if resolve_stage_provider(routing, stage_name) == "cloud":
            return cloud_chat_json(
                routing,
                messages=messages,
                timeout_seconds=timeout_seconds,
            )
    import nimbusware_orchestrator.llm_plan as _patch

    return _patch.ollama_chat_json(
        base_url=base_url,
        model=model,
        messages=messages,
        timeout_seconds=timeout_seconds,
    )


def _fixes_from_llm(raw: object) -> list[RequiredFixArtifact]:
    if not isinstance(raw, list) or not raw:
        return []
    out: list[RequiredFixArtifact] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(RequiredFixArtifact.model_validate(item))
    return out


def execute_post_verify_role_critique_llm(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    base_url: str,
    model_id: str,
    verifier_exit_code: int,
    log_snippet: str,
    producer_role: str,
    stage_name: str,
    evidence_tag: str,
    review_label: str | None = None,
    user_suffix: str | None = None,
    stage_started_metadata: dict[str, object] | None = None,
    timeout_seconds: float = 120.0,
) -> bool:
    from agent_core.context_budget import truncate_for_llm_history

    owner = registry.resolve(producer_role)
    tax_keys = critique_router.pairing_for(producer_role)
    if len(tax_keys) < 2:
        return False
    tax_key_union = "|".join(f'"{k}"' for k in tax_keys)
    system = (
        "You are a Nimbusware orchestration helper. Reply with JSON only. "
        f'Schema: {{"critics":[{{"tax_key":{tax_key_union},'
        '"verdict":"PASS"|"FAIL","severity":"LOW"|"MEDIUM"|"HIGH"|"BLOCKER",'
        '"is_in_domain":true|false,"evidence_refs":["string"],'
        '"required_fixes":[]}],"gate":{"verdict":"PASS"|"FAIL"}}. '
        "For FAIL verdict each critic must include non-empty required_fixes with "
        "artifact_schema_version=1, format=json_patch, target_files, patch_artifact, "
        "validation_steps, acceptance_criteria. Prefer PASS when the log looks healthy."
    )
    bounded = truncate_for_llm_history(log_snippet or "", max_chars=4000)
    if review_label:
        user = (
            f"Post-verify {review_label} review. Verifier exit_code={verifier_exit_code}. "
            f"Last lines of verifier log (truncated):\n{bounded}"
        )
    else:
        user = (
            f"Verifier exit_code={verifier_exit_code}. "
            f"Last lines of verifier log (truncated):\n{bounded}"
        )
    if user_suffix:
        user = f"{user}\n\n{user_suffix.strip()}"
    try:
        data = ollama_chat_json_via_plan_patch(
            base_url=base_url,
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout_seconds=timeout_seconds,
            stage_name=stage_name,
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

    stage_event_kwargs: dict[str, object] = {
        "event_type": EventType.STAGE_STARTED,
        "event_id": uuid4(),
        "run_id": run_id,
        "occurred_at": datetime.now(timezone.utc),
        "payload": StageStartedPayload(stage_name=stage_name, attempt=1),
    }
    if stage_started_metadata is not None:
        stage_event_kwargs["metadata"] = stage_started_metadata
    store.append(StageStartedEvent(**stage_event_kwargs))
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
            evidence_refs=evidence_refs or [f"llm://{evidence_tag}"],
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


__all__ = [name for name in globals() if not name.startswith("__")]
