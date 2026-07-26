"""Harness gate/event helpers retained after sak411 common.py delete."""

from __future__ import annotations

import json
from collections.abc import Callable
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
from broker_client.flags import broker_llm_enabled
from env.env_flags import nimbusware_repo_root_path
from extensions.extension_runtime import UniversalCritiqueRouter
from orchestrator.critique.unanimous_gate import gate_decision_from_critic_verdicts
from orchestrator.llm.chat_facade import ollama_chat_json_via_plan_patch
from orchestrator.llm.peel_guard import _llm_broker_miss_or_transport  # sak499-e
from orchestrator.registry import RoleRegistry
from research.planner_context import planner_research_context_from_events
from store.protocol import EventStore

MODULE_INTEGRATOR_CRITIQUE_STAGE = "module_integrator.critique"
SELF_REFINEMENT_CRITIQUE_STAGE = "self_refinement.critique"
AGENT_EVALUATOR_POLICY_STAGE = "agent_evaluator.policy"

_ROLE_CRITIQUE_BROKER_MISS = "broker_miss: post_verify_role_critique"
_SELF_REFINEMENT_CRITIQUE_BROKER_MISS = "broker_miss: self_refinement_critique"
_AGENT_EVALUATOR_POLICY_BROKER_MISS = "broker_miss: agent_evaluator_policy"


class _LlmCriticLine(BaseModel):
    model_config = {"extra": "ignore"}

    tax_key: str = Field(min_length=1)
    verdict: str = "PASS"
    severity: str = "LOW"
    is_in_domain: bool = True
    evidence_refs: list[str] | None = None
    required_fixes: list[dict[str, Any]] = Field(default_factory=list)


class _LlmGateLine(BaseModel):
    model_config = {"extra": "ignore"}

    verdict: str = "PASS"


class _LlmPlanResponse(BaseModel):
    model_config = {"extra": "ignore"}

    critics: list[_LlmCriticLine] = Field(min_length=2)
    gate: _LlmGateLine


class _LlmSelfRefinementCritiqueResponse(BaseModel):
    model_config = {"extra": "ignore"}

    verdict: str = "PASS"
    gate_decision: str = "hold"
    summary: str = ""


class LlmAgentEvaluatorPolicyResponse(BaseModel):
    model_config = {"extra": "ignore"}

    status: str = "ok"
    gaps: list[str] = Field(default_factory=list)
    summary: str = ""


# Public alias for plan-stage JSON schema (`sak522-b`; was plan_stage.LlmPlanResponse).
LlmPlanResponse = _LlmPlanResponse


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
    from orchestrator.integrator.gate import workflow_profile_from_run_created_rows
    from orchestrator.workflow.universal_critique import effective_universal_critique

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
    from broker_client.flags import broker_llm_enabled

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
            peel_strict=True,  # sak497-h
        )
        parsed = _LlmPlanResponse.model_validate(data)
    except RuntimeError as exc:
        if broker_llm_enabled():  # sak497-h
            raise
        if _llm_broker_miss_or_transport(exc):  # sak499-e
            return False
        raise
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
    ):
        if broker_llm_enabled():  # sak497-h
            raise RuntimeError(_ROLE_CRITIQUE_BROKER_MISS) from None
        return False

    stage_event_kwargs: dict[str, Any] = {
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
    """sak498-c: broker-chat self-refinement critique with peel_strict."""
    from agent_core.context_budget import truncate_for_llm_history
    from broker_client.flags import broker_llm_enabled

    owner = registry.resolve("planner")
    tax_keys = critique_router.pairing_for("planner")
    if len(tax_keys) < 1:
        return None
    system = (
        "You are a Nimbusware self-refinement orchestration helper. Reply with JSON only. "
        'Schema: {"verdict":"PASS"|"FAIL","gate_decision":"proceed"|"hold",'
        '"summary":"string"}. Recommend proceed only when gaps are minor or the '
        "policy description indicates readiness; otherwise hold."
    )
    bounded_desc = truncate_for_llm_history(description or "")
    user = (
        f"evaluation_status={evaluation_status!r}. gaps={list(gaps)!r}. "
        f"policy_description={bounded_desc!r}"
    )
    stage_name = SELF_REFINEMENT_CRITIQUE_STAGE
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
            peel_strict=True,  # sak498-c
        )
        parsed = _LlmSelfRefinementCritiqueResponse.model_validate(data)
    except RuntimeError as exc:
        if broker_llm_enabled():  # sak498-c
            raise
        if _llm_broker_miss_or_transport(exc):  # sak499-e
            return None
        raise
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
    ):
        if broker_llm_enabled():  # sak498-c
            raise RuntimeError(_SELF_REFINEMENT_CRITIQUE_BROKER_MISS) from None
        return None

    verdict = _parse_verdict(parsed.verdict)
    gate_raw = str(parsed.gate_decision).strip().lower()
    gate = "proceed" if gate_raw == "proceed" else "hold"
    summary = str(parsed.summary or "").strip()[:500]
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


def bind_post_verify_role_critique(
    *,
    name: str,
    producer_tax_key: str,
    stage_name: str,
    evidence_tag: str,
    review_label: str | None = None,
    min_pairing_count: int = 2,
    max_critics: int | None = None,
    bind_execute_llm: bool = True,
    self_refinement: bool = False,
) -> tuple[
    Callable[..., None],
    Callable[..., bool | dict[str, str] | None] | None,
]:
    """sak497-h: broker-chat post-verify role critique bindings."""
    label = review_label or producer_tax_key.replace("_", " ")

    def emit_stub_panel(
        store: EventStore,
        registry: RoleRegistry,
        critique_router: UniversalCritiqueRouter,
        *,
        run_id: UUID,
    ) -> None:
        emit_stub_role_critique_panel(
            store,
            registry,
            critique_router,
            run_id=run_id,
            producer_tax_key=producer_tax_key,
            stage_name=stage_name,
            evidence_ref=f"stub://{evidence_tag}",
            min_pairing_count=min_pairing_count,
            max_critics=max_critics,
        )

    if not bind_execute_llm:
        emit_stub_panel.__name__ = f"emit_stub_{name}_critique_panel"
        return emit_stub_panel, None

    if self_refinement:

        def execute_self_refinement_llm(
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
            return execute_self_refinement_critique_llm(
                store,
                registry,
                critique_router,
                run_id=run_id,
                base_url=base_url,
                model_id=model_id,
                evaluation_status=evaluation_status,
                gaps=gaps,
                description=description,
                timeout_seconds=timeout_seconds,
            )

        emit_stub_panel.__name__ = f"emit_stub_{name}_critique_panel"
        execute_self_refinement_llm.__name__ = f"execute_{name}_critique_llm"
        return emit_stub_panel, execute_self_refinement_llm

    def execute_llm(
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
        return execute_post_verify_role_critique_llm(
            store,
            registry,
            critique_router,
            run_id=run_id,
            base_url=base_url,
            model_id=model_id,
            verifier_exit_code=verifier_exit_code,
            log_snippet=log_snippet,
            producer_role=producer_tax_key,
            stage_name=stage_name,
            evidence_tag=evidence_tag,
            review_label=label,
            timeout_seconds=timeout_seconds,
        )

    emit_stub_panel.__name__ = f"emit_stub_{name}_critique_panel"
    execute_llm.__name__ = f"execute_{name}_critique_llm"
    return emit_stub_panel, execute_llm


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
    """Broker-first agent-evaluator policy JSON (`sak522-a`; was agent_evaluator.py)."""
    _ = store, registry, run_id
    pid = str(persona_id).strip() or "default"
    rules_status = rules_eval.get("status")
    rules_gaps = rules_eval.get("gaps")
    gaps_list = [str(g) for g in rules_gaps] if isinstance(rules_gaps, list) else []
    system = (
        "You are a Nimbusware agent-evaluator policy helper. Reply with JSON only. "
        "Schema: status ok|needs_work|invalid, gaps string array, summary string. "
        "Complement rules evaluation; do not contradict obvious invalid shelf states."
    )
    user = f"persona_id={pid!r}. rules_status={rules_status!r}. rules_gaps={gaps_list!r}"
    try:
        data = ollama_chat_json_via_plan_patch(
            base_url=base_url,
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout_seconds=timeout_seconds,
            stage_name=AGENT_EVALUATOR_POLICY_STAGE,
            peel_strict=True,  # sak498-d
        )
        parsed = LlmAgentEvaluatorPolicyResponse.model_validate(data)
    except RuntimeError as exc:
        if broker_llm_enabled():  # sak498-d
            raise
        if _llm_broker_miss_or_transport(exc):  # sak499-e
            return None
        raise
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
    ):
        if broker_llm_enabled():  # sak498-d
            raise RuntimeError(_AGENT_EVALUATOR_POLICY_BROKER_MISS) from None
        return None
    status_raw = str(parsed.status).strip().lower()
    if status_raw in ("ok", "needs_work", "invalid"):
        status_out = status_raw
    else:
        status_out = "needs_work"
    gaps_out = [str(g).strip() for g in parsed.gaps if str(g).strip()][:20]
    summary = str(parsed.summary or "").strip()[:500]
    return {"status": status_out, "gaps": gaps_out, "summary": summary}


def _plan_stage_user_prompt(store: EventStore, run_id: UUID) -> str:
    base = "Evaluate the plan stage for a generic software delivery plan."
    rows = store.list_run_events(str(run_id))
    research_ctx = planner_research_context_from_events(rows)
    if not research_ctx.strip():
        return base
    return f"{research_ctx.strip()}\n\n{base}"


def _plan_evidence_refs(store: EventStore, run_id: UUID, *, prefix: str) -> list[str]:
    refs = [prefix]
    rows = store.list_run_events(str(run_id))
    if planner_research_context_from_events(rows).strip():
        refs.append("research://briefs-merged")
    return refs


def _plan_deliverables(requirements: dict[str, Any] | None) -> list[str]:
    if not isinstance(requirements, dict):
        return ["Deliver bounded slices with tests and gate verification"]
    prompt = str(requirements.get("business_prompt") or requirements.get("prompt") or "").strip()
    if not prompt:
        return ["Deliver bounded slices with tests and gate verification"]
    try:
        from orchestrator.campaign.heuristic_templates import (
            HEURISTIC_TEMPLATES,
            match_template_id,
        )

        template = (
            HEURISTIC_TEMPLATES.get(match_template_id(prompt)) or HEURISTIC_TEMPLATES["generic"]
        )
        return [f"{spec.title}: {spec.rationale}" for spec in template.slices]
    except ImportError:
        pass
    parts = [p.strip() for p in prompt.replace("\n", ". ").split(".") if p.strip()]
    return parts[:6] if parts else [prompt[:240]]


def emit_deterministic_plan_stage(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    requirements: dict[str, Any] | None = None,
) -> None:
    planner = registry.resolve("planner")
    critic_roles = [registry.resolve(tax_key) for tax_key in critique_router.pairing_for("planner")]
    deliverables = _plan_deliverables(requirements)
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
    evidence_refs = _plan_evidence_refs(store, run_id, prefix="requirements://plan")
    evidence_refs.append(f"requirements://deliverables/{len(deliverables)}")
    for critic_role in critic_roles:
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=Verdict.PASS,
            severity=Severity.LOW,
            owner_role=planner,
            is_in_domain=True,
            evidence_refs=evidence_refs,
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


def emit_stub_plan_stage(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
) -> None:
    rows = store.list_run_events(str(run_id))
    requirements: dict[str, Any] | None = None
    for row in rows:
        if row.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = row.get("metadata")
        if isinstance(meta, dict):
            req = meta.get("requirements")
            if isinstance(req, dict):
                requirements = req
        break
    emit_deterministic_plan_stage(
        store,
        registry,
        critique_router,
        run_id=run_id,
        requirements=requirements,
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
    """Broker-first plan stage (`sak522-b`; was plan_stage.py / sak497-b peel_strict)."""
    planner = registry.resolve("planner")
    plan_critics = critique_router.pairing_for("planner")
    if len(plan_critics) < 2:
        emit_stub_plan_stage(store, registry, critique_router, run_id=run_id)
        return
    tax_key_union = "|".join(f'"{k}"' for k in plan_critics)
    from config.skills_index import load_skill, skill_briefs_prompt_block

    skill_block = skill_briefs_prompt_block()
    plan_skill = ""
    try:
        plan_skill = load_skill("plan-quality")
    except OSError:
        plan_skill = ""
    system = (
        "You are a Nimbusware orchestration helper. Reply with JSON only. "
        f'Schema: {{"critics":[{{"tax_key":{tax_key_union},'
        '"verdict":"PASS"|"FAIL","severity":"LOW"|"MEDIUM"|"HIGH"|"BLOCKER",'
        '"is_in_domain":true|false,"evidence_refs":["string"],'
        '"required_fixes":[]}],"gate":{"verdict":"PASS"|"FAIL"}}. '
        "For FAIL verdict each critic must include non-empty required_fixes with "
        "artifact_schema_version=1, format=json_patch, target_files, patch_artifact, "
        "validation_steps, acceptance_criteria. Prefer PASS for a generic plan."
    )
    user = _plan_stage_user_prompt(store, run_id)
    from agent_core.prompt_tiers import assemble_prompt

    context_tier = skill_block or ""
    if plan_skill.strip():
        context_tier = f"{context_tier}\n\nLoaded skill plan-quality:\n{plan_skill.strip()}".strip()
    messages = assemble_prompt(stable=system, context=context_tier, volatile=user)
    try:
        data = ollama_chat_json_via_plan_patch(
            base_url=base_url,
            model=model_id,
            messages=messages,
            timeout_seconds=timeout_seconds,
            stage_name="plan",
            peel_strict=True,  # sak497-b
        )
        plan = LlmPlanResponse.model_validate(data)
    except RuntimeError:
        raise
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
    ):
        if broker_llm_enabled():  # sak497-b
            raise
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
        if not evidence_refs:
            evidence_refs = _plan_evidence_refs(store, run_id, prefix="llm://plan")
        elif not any(r.startswith("research://") for r in evidence_refs):
            evidence_refs = _plan_evidence_refs(
                store,
                run_id,
                prefix=evidence_refs[0],
            )
        fixes = _fixes_from_llm(c.required_fixes)
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=severity,
            owner_role=planner,
            is_in_domain=c.is_in_domain,
            evidence_refs=evidence_refs,
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


def __getattr__(name: str):
    def _gone(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(f"orchestrator.llm.common.{name} removed (sak411)")

    return _gone
