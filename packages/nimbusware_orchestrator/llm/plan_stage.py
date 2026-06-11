from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import httpx
from pydantic import ValidationError

from agent_core.models import (
    CriticVerdictEmittedEvent,
    CriticVerdictEmittedPayload,
    EventType,
    Severity,
    StageStartedEvent,
    StageStartedPayload,
    Verdict,
)
from nimbusware_extensions.phase2 import UniversalCritiqueRouter
from nimbusware_orchestrator.llm.common import (
    IMPLEMENTATION_CRITIQUE_STAGE,
    LlmPlanResponse,
    _finalize_critique_gate,
    _fixes_from_llm,
    _parse_severity,
    _parse_verdict,
)
from nimbusware_orchestrator.llm.common import (
    ollama_chat_json_via_plan_patch as _ollama_chat_json,
)
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_research.planner_context import planner_research_context_from_events
from nimbusware_store.protocol import EventStore


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


def emit_stub_plan_stage(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
) -> None:
    """Deterministic PASS plan stage (same semantics as MVP stub in ``pipeline``)."""
    planner = registry.resolve("planner")
    critic_roles = [registry.resolve(tax_key) for tax_key in critique_router.pairing_for("planner")]
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
    evidence_refs = _plan_evidence_refs(store, run_id, prefix="stub://mvp")
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


def emit_stub_implementation_critique_panel(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
) -> None:
    """PASS critic + gate events for ``backend_writer``.

    Paired critics come from ``critique_pairings.yaml``. Caller must gate on
    ``NIMBUSWARE_STUB_IMPLEMENTATION_CRITICS`` (or equivalent) so default runs stay
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
    from nimbusware_config.skills_index import load_skill, skill_briefs_prompt_block

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
    from nimbusware_orchestrator.prompt_tiers import assemble_prompt

    context_tier = skill_block or ""
    if plan_skill.strip():
        context_tier = f"{context_tier}\n\nLoaded skill plan-quality:\n{plan_skill.strip()}".strip()
    messages = assemble_prompt(stable=system, context=context_tier, volatile=user)
    try:
        data = _ollama_chat_json(
            base_url=base_url,
            model=model_id,
            messages=messages,
            timeout_seconds=timeout_seconds,
            stage_name="plan",
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
