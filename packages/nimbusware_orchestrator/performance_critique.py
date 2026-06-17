from __future__ import annotations

import json
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
from nimbusware_extensions.phase2 import UniversalCritiqueRouter
from nimbusware_orchestrator.llm.common import (
    append_gate_decision_event,
    ollama_chat_json_via_plan_patch,
)
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.scan_stub_critique_emit import (
    ScanStubCritiqueConfig,
    emit_scan_stub_critique_panel,
)
from nimbusware_orchestrator.unanimous_gate import gate_decision_from_critic_verdicts
from nimbusware_orchestrator.workflow_scan_critique import (
    PerformanceCritiqueBlock,
    scan_critique_gate_timeline_summary,
    severity_for_critique_floor,
)
from nimbusware_store.protocol import EventStore

PERFORMANCE_CRITIQUE_STAGE = "implementation.performance_critique"
_PERFORMANCE_CRITIC = "performance_critic"
_PERF_TOOLS = ("ruff_perf", "n_plus_one_heuristic", "sql_profiler")

_PERFORMANCE_STUB_CONFIG = ScanStubCritiqueConfig(
    stage_name=PERFORMANCE_CRITIQUE_STAGE,
    metadata_key="performance_critique",
    specialist_tax_key=_PERFORMANCE_CRITIC,
    evidence_scheme="perf",
    evidence_ok="perf://clean",
    mirror_evidence="perf://paired_mirror",
)


class PerformanceCritiqueLlmResponse(BaseModel):
    model_config = {"extra": "ignore"}

    verdict: str = "PASS"
    summary: str = ""


def performance_scan_tools_failed(tool_summary: dict[str, Any]) -> tuple[bool, list[str]]:
    tools = tool_summary.get("security_scan_tools")
    if not isinstance(tools, dict):
        return False, []
    failing: list[str] = []
    for name in _PERF_TOOLS:
        try:
            code = int(tools.get(name, 0))
        except (TypeError, ValueError):
            code = 0
        if code != 0:
            failing.append(name)
    return bool(failing), failing


def performance_critique_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    return scan_critique_gate_timeline_summary(
        events,
        stage_name=PERFORMANCE_CRITIQUE_STAGE,
    )


def _required_fix_for_perf(failing: list[str]) -> RequiredFixArtifact:
    return RequiredFixArtifact.model_validate(
        {
            "artifact_schema_version": 1,
            "format": "json_patch",
            "target_files": ["packages/"],
            "patch_artifact": "[]",
            "validation_steps": [f"resolve performance findings: {', '.join(failing)}"],
            "acceptance_criteria": "ruff_perf and N+1 heuristic pass",
        },
    )


def emit_stub_performance_critique_panel(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    producer_tax_key: str,
    scan_summary: dict[str, Any],
    block: PerformanceCritiqueBlock,
    unanimous_gate_enforce: bool = False,
) -> None:
    failed, failing = performance_scan_tools_failed(scan_summary)
    fixes = [_required_fix_for_perf(failing)] if failing else []
    emit_scan_stub_critique_panel(
        store,
        registry,
        critique_router,
        run_id=run_id,
        producer_tax_key=producer_tax_key,
        scan_summary=scan_summary,
        block=block,
        config=_PERFORMANCE_STUB_CONFIG,
        failed=failed,
        failing_items=failing,
        fixes=fixes,
        unanimous_gate_enforce=unanimous_gate_enforce,
    )


def execute_performance_critique_llm(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    producer_tax_key: str,
    scan_summary: dict[str, Any],
    base_url: str,
    model_id: str,
    block: PerformanceCritiqueBlock,
    timeout_seconds: float = 120.0,
    unanimous_gate_enforce: bool = False,
) -> bool:
    tax_keys = critique_router.pairing_for(producer_tax_key)
    if _PERFORMANCE_CRITIC not in tax_keys:
        return False
    failed, failing = performance_scan_tools_failed(scan_summary)
    try:
        raw = ollama_chat_json_via_plan_patch(
            base_url=base_url,
            model=model_id,
            messages=[
                {
                    "role": "system",
                    "content": (
                        'Return JSON only: {"verdict":"PASS"|"FAIL","summary":"string"}. '
                        "FAIL when ruff_perf or n_plus_one_heuristic report issues."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "tools": scan_summary.get("security_scan_tools"),
                            "failing": failing,
                        },
                    ),
                },
            ],
            timeout_seconds=timeout_seconds,
            agent_role="security_critic",
        )
        parsed = PerformanceCritiqueLlmResponse.model_validate(raw)
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
    owner = registry.resolve(producer_tax_key)
    severity = severity_for_critique_floor(block.severity_floor)
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"performance_critique": {"branch": "llm"}},
            payload=StageStartedPayload(stage_name=PERFORMANCE_CRITIQUE_STAGE, attempt=1),
        ),
    )
    critic_payloads: list[CriticVerdictEmittedPayload] = []
    fail_any = llm_fail or failed
    fixes = [_required_fix_for_perf(failing)] if fail_any else []
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        verdict = (
            Verdict.FAIL
            if fail_any and tax_key == _PERFORMANCE_CRITIC
            else (Verdict.FAIL if fail_any else Verdict.PASS)
        )
        if tax_key != _PERFORMANCE_CRITIC:
            verdict = Verdict.PASS if not fail_any else Verdict.FAIL
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=severity if verdict == Verdict.FAIL else Severity.LOW,
            owner_role=owner,
            is_in_domain=tax_key == _PERFORMANCE_CRITIC,
            evidence_refs=["perf://llm"],
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
        stage_name=PERFORMANCE_CRITIQUE_STAGE,
        unanimous_pass_required=True,
        enforce=unanimous_gate_enforce or fail_any,
    )
    append_gate_decision_event(store, run_id=run_id, payload=gate)
    return True
