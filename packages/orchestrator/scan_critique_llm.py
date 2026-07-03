from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any, Literal
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
from extensions.extension_runtime import UniversalCritiqueRouter
from orchestrator.llm.common import (
    append_gate_decision_event,
    ollama_chat_json_via_plan_patch,
)
from orchestrator.registry import RoleRegistry
from orchestrator.unanimous_gate import gate_decision_from_critic_verdicts
from orchestrator.workflow_scan_critique import severity_for_critique_floor
from store.protocol import EventStore

VerdictMode = Literal["mirror", "uniform"]
_LlmFailedFn = Callable[[Any, bool, list[str]], bool]
_BuildUserContent = Callable[[Mapping[str, Any], bool, list[str]], str]
_BuildFixes = Callable[[list[str], Any], list[RequiredFixArtifact]]
_BuildStageMetadata = Callable[[Mapping[str, Any], Any], dict[str, Any]]
_EvidenceRefFn = Callable[[str], str]


def execute_scan_critique_llm(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    producer_tax_key: str,
    scan_summary: dict[str, Any],
    base_url: str,
    model_id: str,
    block: Any,
    stage_name: str,
    metadata_key: str,
    specialist_tax_key: str,
    response_model: type[BaseModel],
    system_prompt: str,
    build_user_content: _BuildUserContent,
    scan_failed_fn: Callable[[dict[str, Any]], tuple[bool, list[str]]],
    build_fixes_fn: _BuildFixes,
    llm_failed_fn: _LlmFailedFn,
    build_stage_metadata: _BuildStageMetadata | None = None,
    evidence_ref_fn: _EvidenceRefFn | None = None,
    min_pairing_count: int = 1,
    require_specialist_in_pairing: bool = True,
    verdict_mode: VerdictMode = "mirror",
    timeout_seconds: float = 120.0,
    unanimous_gate_enforce: bool = False,
    agent_role: str = "security_critic",
) -> bool:
    tax_keys = critique_router.pairing_for(producer_tax_key)
    if len(tax_keys) < min_pairing_count:
        return False
    if require_specialist_in_pairing and specialist_tax_key not in tax_keys:
        return False
    tool_failed, failing = scan_failed_fn(scan_summary)
    try:
        raw = ollama_chat_json_via_plan_patch(
            base_url=base_url,
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": build_user_content(scan_summary, tool_failed, failing),
                },
            ],
            timeout_seconds=timeout_seconds,
            agent_role=agent_role,
        )
        parsed = response_model.model_validate(raw)
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        ValidationError,
        KeyError,
        RuntimeError,
    ):
        return False

    llm_fail = llm_failed_fn(parsed, tool_failed, failing)
    fail_any = llm_fail or tool_failed
    owner = registry.resolve(producer_tax_key)
    severity = severity_for_critique_floor(block.severity_floor)
    stage_meta = {metadata_key: {"branch": "llm"}}
    if build_stage_metadata is not None:
        stage_meta[metadata_key] = {
            **stage_meta[metadata_key],
            **build_stage_metadata(scan_summary, parsed),
        }
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
    fixes = build_fixes_fn(failing, parsed) if fail_any else []
    critic_payloads: list[CriticVerdictEmittedPayload] = []
    ref_fn = evidence_ref_fn or (lambda tax_key: f"scan://{tax_key}")
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        if verdict_mode == "uniform":
            verdict = Verdict.FAIL if fail_any else Verdict.PASS
            in_domain = tax_key == specialist_tax_key
        else:
            in_domain = tax_key == specialist_tax_key
            verdict = Verdict.FAIL if fail_any else Verdict.PASS
            if not in_domain:
                verdict = Verdict.PASS if not fail_any else Verdict.FAIL
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=severity if verdict == Verdict.FAIL else Severity.LOW,
            owner_role=owner,
            is_in_domain=in_domain,
            evidence_refs=[ref_fn(tax_key)],
            required_fixes=fixes if verdict == Verdict.FAIL else [],
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
        stage_name=stage_name,
        unanimous_pass_required=True,
        enforce=unanimous_gate_enforce or fail_any,
    )
    append_gate_decision_event(store, run_id=run_id, payload=gate)
    return True
