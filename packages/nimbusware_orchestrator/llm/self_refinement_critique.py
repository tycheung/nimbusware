from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx
from pydantic import ValidationError

from agent_core.context_budget import truncate_for_llm_history
from agent_core.models import (
    CriticVerdictEmittedEvent,
    CriticVerdictEmittedPayload,
    EventType,
    GateDecisionEmittedPayload,
    Severity,
    StageStartedEvent,
    StageStartedPayload,
    Verdict,
)
from nimbusware_extensions.extension_runtime import UniversalCritiqueRouter
from nimbusware_orchestrator.llm.common import (
    SELF_REFINEMENT_CRITIQUE_STAGE,
    LlmSelfRefinementCritiqueResponse,
    _parse_verdict,
    append_gate_decision_event,
)
from nimbusware_orchestrator.llm.common import (
    ollama_chat_json_via_plan_patch as _ollama_chat_json,
)
from nimbusware_orchestrator.llm.post_verify_role_bindings import (
    emit_stub_self_refinement_critique_panel,
)
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_store.protocol import EventStore

__all__ = [
    "emit_stub_self_refinement_critique_panel",
    "execute_self_refinement_critique_llm",
]


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
    try:
        data = _ollama_chat_json(
            base_url=base_url,
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout_seconds=timeout_seconds,
            stage_name=SELF_REFINEMENT_CRITIQUE_STAGE,
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
