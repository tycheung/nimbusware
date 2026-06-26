from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, ValidationError

from agent_core.models import (
    CriticVerdictEmittedEvent,
    CriticVerdictEmittedPayload,
    EventType,
    RequiredFixArtifact,
    Severity,
    StageStartedEvent,
    StageStartedPayload,
    Verdict,
)
from nimbusware_extensions.extension_runtime import UniversalCritiqueRouter
from nimbusware_orchestrator.llm.common import (
    append_gate_decision_event,
    ollama_chat_json_via_plan_patch,
)
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.unanimous_gate import gate_decision_from_critic_verdicts
from nimbusware_store.protocol import EventStore


def execute_persona_rules_critique_llm(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    stage_name: str,
    producer_tax_key: str,
    specialist_tax_key: str,
    rules_eval: dict[str, Any] | None,
    base_url: str,
    model_id: str,
    response_model: type[BaseModel],
    system_prompt: str,
    build_user_content: Callable[[dict[str, Any] | None], str],
    specialist_failed: Callable[[Any, dict[str, Any] | None], bool],
    tax_key_failed: Callable[[str, bool, dict[str, Any] | None], bool],
    build_stage_metadata: Callable[[Any], dict[str, Any]],
    coverage_fix: RequiredFixArtifact,
    evidence_prefix: str,
    min_pairing_count: int = 2,
    timeout_seconds: float = 120.0,
    unanimous_gate_enforce: bool = False,
) -> bool:
    tax_keys = critique_router.pairing_for(producer_tax_key)
    if len(tax_keys) < min_pairing_count:
        return False
    try:
        raw = ollama_chat_json_via_plan_patch(
            base_url=base_url,
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": build_user_content(rules_eval)},
            ],
            timeout_seconds=timeout_seconds,
            agent_role="security_critic",
        )
        parsed = response_model.model_validate(raw)
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
    ):
        return False

    specialist_fail = specialist_failed(parsed, rules_eval)
    owner = registry.resolve(producer_tax_key)
    stage_meta = build_stage_metadata(parsed)
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata=stage_meta,
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        fail = tax_key_failed(tax_key, specialist_fail, rules_eval)
        verdict = Verdict.FAIL if fail else Verdict.PASS
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=Severity.MEDIUM if verdict == Verdict.FAIL else Severity.LOW,
            owner_role=owner,
            is_in_domain=True,
            evidence_refs=[f"{evidence_prefix}/{getattr(parsed, 'status', 'ok')}"],
            required_fixes=[coverage_fix] if verdict == Verdict.FAIL else [],
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
    rules_status = _evaluation_status(rules_eval)
    fail_any = specialist_fail or rules_status in ("invalid", "gap")
    gate = gate_decision_from_critic_verdicts(
        critic_payloads,
        stage_name=stage_name,
        unanimous_pass_required=True,
        enforce=unanimous_gate_enforce or fail_any,
    )
    append_gate_decision_event(store, run_id=run_id, payload=gate)
    return True


def _evaluation_status(rules_eval: Mapping[str, Any] | None) -> str:
    if not isinstance(rules_eval, Mapping):
        return "gap"
    status = rules_eval.get("status")
    if isinstance(status, str) and status.strip():
        return status.strip().lower()
    return "gap"
