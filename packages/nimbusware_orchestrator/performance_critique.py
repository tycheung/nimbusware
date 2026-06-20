from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from agent_core.models import RequiredFixArtifact
from nimbusware_extensions.phase2 import UniversalCritiqueRouter
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.scan_critique_llm import execute_scan_critique_llm
from nimbusware_orchestrator.scan_stub_critique_emit import (
    ScanStubCritiqueConfig,
    emit_scan_stub_critique_panel,
)
from nimbusware_orchestrator.workflow_scan_critique import (
    PerformanceCritiqueBlock,
    scan_critique_gate_timeline_summary,
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
    return execute_scan_critique_llm(
        store,
        registry,
        critique_router,
        run_id=run_id,
        producer_tax_key=producer_tax_key,
        scan_summary=scan_summary,
        base_url=base_url,
        model_id=model_id,
        block=block,
        stage_name=PERFORMANCE_CRITIQUE_STAGE,
        metadata_key="performance_critique",
        specialist_tax_key=_PERFORMANCE_CRITIC,
        response_model=PerformanceCritiqueLlmResponse,
        system_prompt=(
            'Return JSON only: {"verdict":"PASS"|"FAIL","summary":"string"}. '
            "FAIL when ruff_perf or n_plus_one_heuristic report issues."
        ),
        build_user_content=lambda summary, _tf, failing: json.dumps(
            {"tools": summary.get("security_scan_tools"), "failing": failing},
        ),
        scan_failed_fn=performance_scan_tools_failed,
        build_fixes_fn=lambda failing, _parsed: [_required_fix_for_perf(failing or ["llm"])],
        llm_failed_fn=lambda parsed, _tf, _failing: str(parsed.verdict).upper() == "FAIL",
        evidence_ref_fn=lambda _tax_key: "perf://llm",
        timeout_seconds=timeout_seconds,
        unanimous_gate_enforce=unanimous_gate_enforce,
    )
