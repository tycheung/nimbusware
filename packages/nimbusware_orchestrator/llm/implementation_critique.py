from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import httpx
from pydantic import ValidationError

from agent_core.context_budget import truncate_for_llm_history
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
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_store.protocol import EventStore


def _ollama_chat_json(*args: object, **kwargs: object) -> object:
    import nimbusware_orchestrator.llm_plan as _patch

    return _patch.ollama_chat_json(*args, **kwargs)


def emit_stub_implementation_critique_panel(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
) -> None:
    """PASS critic + gate events for ``backend_writer`` (§14 #16 beyond **plan**).

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

    Gating (``NIMBUSWARE_IMPLEMENTATION_CRITIQUE_LLM`` + stub fallback) lives in
    :meth:`nimbusware_orchestrator.pipeline.RunOrchestrator.execute_writer_verifier_pass`.
    """
    owner = registry.resolve("backend_writer")
    tax_keys = critique_router.pairing_for("backend_writer")
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
    from nimbusware_config.skills_index import load_skill

    skill_body = ""
    try:
        skill_body = load_skill("refactor-rubric")
    except OSError:
        skill_body = ""
    bounded = truncate_for_llm_history(log_snippet or "", max_chars=4000)
    user = (
        f"Verifier exit_code={verifier_exit_code}. "
        f"Last lines of verifier log (truncated):\n{bounded}"
    )
    if skill_body.strip():
        user = f"{user}\n\nLoaded skill refactor-rubric:\n{skill_body.strip()}"
    try:
        data = _ollama_chat_json(
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
            metadata={"skill": "skill:refactor-rubric"},
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
