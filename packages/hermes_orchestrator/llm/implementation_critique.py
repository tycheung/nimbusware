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
from hermes_orchestrator.llm.common import *  # noqa: F403

def _ollama_chat_json(*args: object, **kwargs: object) -> object:
    import hermes_orchestrator.llm_plan as _patch
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


