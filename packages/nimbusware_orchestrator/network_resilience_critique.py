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
from nimbusware_orchestrator.llm.common import append_gate_decision_event
from nimbusware_orchestrator.ollama_chat import ollama_chat_json
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.scan_stub_critique_emit import (
    ScanStubCritiqueConfig,
    emit_scan_stub_critique_panel,
)
from nimbusware_orchestrator.unanimous_gate import gate_decision_from_critic_verdicts
from nimbusware_orchestrator.workflow_scan_critique import (
    NetworkResilienceCritiqueBlock,
    scan_critique_gate_timeline_summary,
    severity_for_critique_floor,
)
from nimbusware_store.protocol import EventStore

NETWORK_RESILIENCE_CRITIQUE_STAGE = "implementation.network_resilience_critique"
_NETWORK_RESILIENCE_CRITIC = "network_resilience_critic"

_NETWORK_STUB_CONFIG = ScanStubCritiqueConfig(
    stage_name=NETWORK_RESILIENCE_CRITIQUE_STAGE,
    metadata_key="network_resilience_critique",
    specialist_tax_key=_NETWORK_RESILIENCE_CRITIC,
    evidence_scheme="net",
    evidence_ok="net://ok",
    mirror_evidence="net://paired_mirror",
    metadata_scan_field="scan",
)


class NetworkResilienceLlmResponse(BaseModel):
    model_config = {"extra": "ignore"}

    verdict: str = "PASS"
    summary: str = ""


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
    return scan_critique_gate_timeline_summary(
        events,
        stage_name=NETWORK_RESILIENCE_CRITIQUE_STAGE,
    )


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
    failed, reasons = scan_summary_failed(scan_summary)
    fixes = [_required_fix(reasons)] if reasons else []
    emit_scan_stub_critique_panel(
        store,
        registry,
        critique_router,
        run_id=run_id,
        producer_tax_key="backend_writer",
        scan_summary=scan_summary,
        block=block,
        config=_NETWORK_STUB_CONFIG,
        failed=failed,
        failing_items=reasons,
        fixes=fixes,
        unanimous_gate_enforce=unanimous_gate_enforce,
    )


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
    severity = severity_for_critique_floor(block.severity_floor)
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
