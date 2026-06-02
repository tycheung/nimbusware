"""Security Critic stage after writer verify."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, Field, ValidationError

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
from hermes_extensions.phase2 import UniversalCritiqueRouter
from hermes_orchestrator.llm_plan import append_gate_decision_event
from hermes_orchestrator.ollama_chat import ollama_chat_json
from hermes_orchestrator.registry import RoleRegistry
from hermes_orchestrator.security_scan import run_security_scan, security_scan_tool_summary
from hermes_orchestrator.unanimous_gate import gate_decision_from_critic_verdicts
from hermes_orchestrator.workflow_security_critique import SecurityCritiqueBlock
from hermes_store.protocol import EventStore

SECURITY_CRITIQUE_STAGE = "implementation.security_critique"
_SECURITY_CRITIC = "security_critic"
_SECURITY_TOOLS = ("ruff", "bandit", "mypy")


class SecurityCritiqueLlmResponse(BaseModel):
    model_config = {"extra": "ignore"}

    verdict: str = "PASS"
    summary: str = ""
    failing_tools: list[str] = Field(default_factory=list)


def _severity_for_fail(floor: str) -> Severity:
    mapping = {
        "LOW": Severity.LOW,
        "MEDIUM": Severity.MEDIUM,
        "HIGH": Severity.HIGH,
        "BLOCKER": Severity.BLOCKER,
    }
    return mapping.get(floor.upper(), Severity.MEDIUM)


def security_scan_tools_failed(tool_summary: dict[str, Any]) -> tuple[bool, list[str]]:
    tools = tool_summary.get("security_scan_tools")
    if not isinstance(tools, dict):
        return False, []
    failing: list[str] = []
    for name in _SECURITY_TOOLS:
        try:
            code = int(tools.get(name, 0))
        except (TypeError, ValueError):
            code = 0
        if code != 0:
            failing.append(name)
    return bool(failing), failing


def _required_fix_for_tools(failing: list[str]) -> RequiredFixArtifact:
    return RequiredFixArtifact.model_validate(
        {
            "artifact_schema_version": 1,
            "format": "json_patch",
            "target_files": ["packages/"],
            "patch_artifact": "[]",
            "validation_steps": [
                f"resolve security scan failures: {', '.join(failing)}",
            ],
            "acceptance_criteria": "ruff, bandit, and mypy exit 0 on workspace",
        },
    )


def run_security_scan_summary(workspace: Path) -> dict[str, Any]:
    from hermes_orchestrator.sql_profiler import run_sql_profiler_summary

    scode, slog, ruff_ec, bandit_ec, mypy_ec, perf_ec, n1_ec, semgrep_ec = run_security_scan(
        workspace,
    )
    sql_prof = run_sql_profiler_summary(workspace)
    sql_ec = int(sql_prof.get("sql_profiler_exit", 0))
    summary = security_scan_tool_summary(
        ruff_ec,
        bandit_ec,
        mypy_ec,
        perf_ec,
        n1_ec,
        semgrep_ec,
        sql_ec,
    )
    summary["security_scan_exit"] = max(scode, sql_ec)
    summary["security_scan_snippet"] = "\n".join(slog.splitlines()[:20])
    summary["sql_profiler"] = sql_prof
    return summary


def security_critique_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    last_gate: dict[str, Any] | None = None
    for row in events:
        if row.get("event_type") != "gate.decision.emitted":
            continue
        payload = row.get("payload") or {}
        if payload.get("stage_name") == SECURITY_CRITIQUE_STAGE:
            last_gate = payload
    if last_gate is None:
        return None
    return {
        "stage_name": SECURITY_CRITIQUE_STAGE,
        "verdict": last_gate.get("verdict"),
        "failing_critics": last_gate.get("failing_critics") or [],
    }


def emit_stub_security_critique_panel(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    producer_tax_key: str,
    scan_summary: dict[str, Any],
    block: SecurityCritiqueBlock,
    unanimous_gate_enforce: bool = False,
) -> None:
    tax_keys = critique_router.pairing_for(producer_tax_key)
    if len(tax_keys) < 2:
        return
    owner = registry.resolve(producer_tax_key)
    failed, failing_tools = security_scan_tools_failed(scan_summary)
    severity = _severity_for_fail(block.severity_floor)

    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "security_critique": {
                    "branch": "stub",
                    "scan_summary": scan_summary,
                },
            },
            payload=StageStartedPayload(stage_name=SECURITY_CRITIQUE_STAGE, attempt=1),
        ),
    )

    critic_payloads: list[CriticVerdictEmittedPayload] = []
    fixes = [_required_fix_for_tools(failing_tools)] if failing_tools else []
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        if tax_key == _SECURITY_CRITIC:
            verdict = Verdict.FAIL if failed else Verdict.PASS
            evidence = (
                [f"scan://{t}" for t in failing_tools]
                if failing_tools
                else ["scan://security_tools_clean"]
            )
        else:
            verdict = Verdict.PASS if not failed else Verdict.FAIL
            evidence = ["scan://paired_critic_mirrors_security"]
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=severity if verdict == Verdict.FAIL else Severity.LOW,
            owner_role=owner,
            is_in_domain=tax_key == _SECURITY_CRITIC,
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
        stage_name=SECURITY_CRITIQUE_STAGE,
        unanimous_pass_required=True,
        enforce=unanimous_gate_enforce or failed,
    )
    append_gate_decision_event(store, run_id=run_id, payload=gate)


def execute_security_critique_llm(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    producer_tax_key: str,
    scan_summary: dict[str, Any],
    base_url: str,
    model_id: str,
    block: SecurityCritiqueBlock,
    timeout_seconds: float = 120.0,
    unanimous_gate_enforce: bool = False,
) -> bool:
    tax_keys = critique_router.pairing_for(producer_tax_key)
    if len(tax_keys) < 2:
        return False
    failed, failing_tools = security_scan_tools_failed(scan_summary)
    tools = scan_summary.get("security_scan_tools") or {}
    try:
        raw = ollama_chat_json(
            base_url=base_url,
            model=model_id,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a security critic for Hermes. Return JSON only: "
                        '{"verdict":"PASS"|"FAIL","summary":"string","failing_tools":[]}. '
                        "FAIL when ruff, bandit, or mypy scans report issues."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "tools": tools,
                            "rules_failed": failing_tools,
                            "snippet": scan_summary.get("security_scan_snippet", "")[:1500],
                        },
                    ),
                },
            ],
            timeout_seconds=timeout_seconds,
        )
        parsed = SecurityCritiqueLlmResponse.model_validate(raw)
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

    llm_fail = str(parsed.verdict).upper() == "FAIL" or bool(parsed.failing_tools)
    owner = registry.resolve(producer_tax_key)
    severity = _severity_for_fail(block.severity_floor)

    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "security_critique": {
                    "branch": "llm",
                    "llm_summary": str(parsed.summary).strip()[:500],
                    "scan_summary": scan_summary,
                },
            },
            payload=StageStartedPayload(stage_name=SECURITY_CRITIQUE_STAGE, attempt=1),
        ),
    )

    critic_payloads: list[CriticVerdictEmittedPayload] = []
    fixes = (
        [_required_fix_for_tools(failing_tools or list(parsed.failing_tools))] if llm_fail else []
    )
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        if tax_key == _SECURITY_CRITIC:
            fail = llm_fail or failed
        else:
            fail = llm_fail or failed
        verdict = Verdict.FAIL if fail else Verdict.PASS
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=severity if verdict == Verdict.FAIL else Severity.LOW,
            owner_role=owner,
            is_in_domain=tax_key == _SECURITY_CRITIC,
            evidence_refs=[f"scan://{tax_key}"],
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
        stage_name=SECURITY_CRITIQUE_STAGE,
        unanimous_pass_required=True,
        enforce=unanimous_gate_enforce or llm_fail or failed,
    )
    append_gate_decision_event(store, run_id=run_id, payload=gate)
    return True
