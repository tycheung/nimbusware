"""Network/Resilience Critic stage."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, ValidationError

from agent_core.context_budget import truncate_for_llm_history
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
from nimbusware_extensions.phase2 import UniversalCritiqueRouter
from nimbusware_orchestrator.llm_plan import append_gate_decision_event
from nimbusware_orchestrator.ollama_chat import ollama_chat_json
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.unanimous_gate import gate_decision_from_critic_verdicts
from nimbusware_orchestrator.workflow_network_resilience_critique import (
    NetworkResilienceCritiqueBlock,
)
from nimbusware_store.protocol import EventStore

NETWORK_RESILIENCE_CRITIQUE_STAGE = "implementation.network_resilience_critique"
_NETWORK_RESILIENCE_CRITIC = "network_resilience_critic"


class NetworkResilienceLlmResponse(BaseModel):
    model_config = {"extra": "ignore"}

    verdict: str = "PASS"
    summary: str = ""


def _severity_for_fail(floor: str) -> Severity:
    mapping = {
        "LOW": Severity.LOW,
        "MEDIUM": Severity.MEDIUM,
        "HIGH": Severity.HIGH,
        "BLOCKER": Severity.BLOCKER,
    }
    return mapping.get(floor.upper(), Severity.MEDIUM)


def scan_summary_failed(scan_summary: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if int(scan_summary.get("http_resilience_exit", 0)) != 0:
        reasons.append("http_resilience")
    if int(scan_summary.get("sql_query_budget_exit", 0)) != 0:
        reasons.append("sql_query_budget")
    return bool(reasons), reasons


def network_resilience_critique_timeline_summary(
    events: list[dict[str, Any]],
) -> dict[str, Any] | None:
    last_gate: dict[str, Any] | None = None
    for row in events:
        if row.get("event_type") != "gate.decision.emitted":
            continue
        payload = row.get("payload") or {}
        if payload.get("stage_name") == NETWORK_RESILIENCE_CRITIQUE_STAGE:
            last_gate = payload
    if last_gate is None:
        return None
    return {
        "stage_name": NETWORK_RESILIENCE_CRITIQUE_STAGE,
        "verdict": last_gate.get("verdict"),
        "failing_critics": last_gate.get("failing_critics") or [],
    }


def _required_fix(reasons: list[str]) -> RequiredFixArtifact:
    return RequiredFixArtifact.model_validate(
        {
            "artifact_schema_version": 1,
            "format": "json_patch",
            "target_files": ["packages/"],
            "patch_artifact": "[]",
            "validation_steps": [f"resolve network/resilience: {', '.join(reasons)}"],
            "acceptance_criteria": "HTTP clients use timeouts; SQL query budget respected",
        },
    )


def emit_stub_network_resilience_critique_panel(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    scan_summary: dict[str, Any],
    block: NetworkResilienceCritiqueBlock,
    unanimous_gate_enforce: bool = False,
) -> None:
    tax_keys = critique_router.pairing_for("backend_writer")
    if _NETWORK_RESILIENCE_CRITIC not in tax_keys:
        return
    owner = registry.resolve("backend_writer")
    failed, reasons = scan_summary_failed(scan_summary)
    severity = _severity_for_fail(block.severity_floor)
    fixes = [_required_fix(reasons)] if reasons else []

    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"network_resilience_critique": {"branch": "stub", "scan": scan_summary}},
            payload=StageStartedPayload(
                stage_name=NETWORK_RESILIENCE_CRITIQUE_STAGE,
                attempt=1,
            ),
        ),
    )

    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        if tax_key == _NETWORK_RESILIENCE_CRITIC:
            verdict = Verdict.FAIL if failed else Verdict.PASS
            evidence = [f"net://{r}" for r in reasons] if reasons else ["net://ok"]
            in_domain = True
        else:
            verdict = Verdict.PASS if not failed else Verdict.FAIL
            evidence = ["net://paired_mirror"]
            in_domain = False
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=severity if verdict == Verdict.FAIL else Severity.LOW,
            owner_role=owner,
            is_in_domain=in_domain,
            evidence_refs=evidence,
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
        stage_name=NETWORK_RESILIENCE_CRITIQUE_STAGE,
        unanimous_pass_required=True,
        enforce=unanimous_gate_enforce or failed,
    )
    append_gate_decision_event(store, run_id=run_id, payload=gate)


def execute_network_resilience_critique_llm(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    scan_summary: dict[str, Any],
    base_url: str,
    model_id: str,
    block: NetworkResilienceCritiqueBlock,
    timeout_seconds: float = 120.0,
    unanimous_gate_enforce: bool = False,
) -> bool:
    tax_keys = critique_router.pairing_for("backend_writer")
    if _NETWORK_RESILIENCE_CRITIC not in tax_keys:
        return False
    failed, reasons = scan_summary_failed(scan_summary)
    try:
        raw = ollama_chat_json(
            base_url=base_url,
            model=model_id,
            messages=[
                {
                    "role": "system",
                    "content": (
                        'Return JSON only: {"verdict":"PASS"|"FAIL","summary":"string"}. '
                        "FAIL when HTTP resilience or SQL query budget checks failed."
                    ),
                },
                {
                    "role": "user",
                    "content": truncate_for_llm_history(json.dumps(scan_summary), max_chars=4000),
                },
            ],
            timeout_seconds=timeout_seconds,
        )
        parsed = NetworkResilienceLlmResponse.model_validate(raw)
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

    llm_fail = str(parsed.verdict).upper() == "FAIL"
    owner = registry.resolve("backend_writer")
    severity = _severity_for_fail(block.severity_floor)
    fail_any = llm_fail or failed
    fixes = [_required_fix(reasons or ["llm"])] if fail_any else []

    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"network_resilience_critique": {"branch": "llm"}},
            payload=StageStartedPayload(
                stage_name=NETWORK_RESILIENCE_CRITIQUE_STAGE,
                attempt=1,
            ),
        ),
    )

    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        verdict = (
            Verdict.FAIL
            if fail_any and tax_key == _NETWORK_RESILIENCE_CRITIC
            else (Verdict.FAIL if fail_any else Verdict.PASS)
        )
        if tax_key != _NETWORK_RESILIENCE_CRITIC:
            verdict = Verdict.PASS if not fail_any else Verdict.FAIL
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=severity if verdict == Verdict.FAIL else Severity.LOW,
            owner_role=owner,
            is_in_domain=tax_key == _NETWORK_RESILIENCE_CRITIC,
            evidence_refs=["net://llm"],
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
        stage_name=NETWORK_RESILIENCE_CRITIQUE_STAGE,
        unanimous_pass_required=True,
        enforce=unanimous_gate_enforce or fail_any,
    )
    append_gate_decision_event(store, run_id=run_id, payload=gate)
    return True
