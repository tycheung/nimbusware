"""Performance Critic stage after security critique."""

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
from nimbusware_orchestrator.llm.common import append_gate_decision_event
from nimbusware_orchestrator.ollama_chat import ollama_chat_json
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.unanimous_gate import gate_decision_from_critic_verdicts
from nimbusware_orchestrator.workflow_performance_critique import PerformanceCritiqueBlock
from nimbusware_store.protocol import EventStore

PERFORMANCE_CRITIQUE_STAGE = "implementation.performance_critique"
_PERFORMANCE_CRITIC = "performance_critic"
_PERF_TOOLS = ("ruff_perf", "n_plus_one_heuristic", "sql_profiler")


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
    last_gate: dict[str, Any] | None = None
    for row in events:
        if row.get("event_type") != "gate.decision.emitted":
            continue
        payload = row.get("payload") or {}
        if payload.get("stage_name") == PERFORMANCE_CRITIQUE_STAGE:
            last_gate = payload
    if last_gate is None:
        return None
    return {
        "stage_name": PERFORMANCE_CRITIQUE_STAGE,
        "verdict": last_gate.get("verdict"),
        "failing_critics": last_gate.get("failing_critics") or [],
    }


def _severity_for_fail(floor: str) -> Severity:
    mapping = {
        "LOW": Severity.LOW,
        "MEDIUM": Severity.MEDIUM,
        "HIGH": Severity.HIGH,
        "BLOCKER": Severity.BLOCKER,
    }
    return mapping.get(floor.upper(), Severity.MEDIUM)


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
    tax_keys = critique_router.pairing_for(producer_tax_key)
    if _PERFORMANCE_CRITIC not in tax_keys:
        return
    owner = registry.resolve(producer_tax_key)
    failed, failing = performance_scan_tools_failed(scan_summary)
    severity = _severity_for_fail(block.severity_floor)

    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"performance_critique": {"branch": "stub", "scan_summary": scan_summary}},
            payload=StageStartedPayload(stage_name=PERFORMANCE_CRITIQUE_STAGE, attempt=1),
        ),
    )

    critic_payloads: list[CriticVerdictEmittedPayload] = []
    fixes = [_required_fix_for_perf(failing)] if failing else []
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        if tax_key == _PERFORMANCE_CRITIC:
            verdict = Verdict.FAIL if failed else Verdict.PASS
            evidence = [f"perf://{t}" for t in failing] if failing else ["perf://clean"]
            in_domain = True
        else:
            verdict = Verdict.PASS if not failed else Verdict.FAIL
            evidence = ["perf://paired_mirror"]
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
        stage_name=PERFORMANCE_CRITIQUE_STAGE,
        unanimous_pass_required=True,
        enforce=unanimous_gate_enforce or failed,
    )
    append_gate_decision_event(store, run_id=run_id, payload=gate)


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
        raw = ollama_chat_json(
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
    severity = _severity_for_fail(block.severity_floor)
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
