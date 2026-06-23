from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from nimbusware_extensions.phase2 import UniversalCritiqueRouter
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.scan_critique_kinds import (
    PERFORMANCE_KIND,
    PerformanceCritiqueLlmResponse,
    emit_stub_panel,
    execute_llm,
    required_fix_artifact,
    timeline_summary,
    tools_failed,
)
from nimbusware_orchestrator.workflow_scan_critique import PerformanceCritiqueBlock
from nimbusware_store.protocol import EventStore

PERFORMANCE_CRITIQUE_STAGE = PERFORMANCE_KIND.stage_name
performance_critique_timeline_summary = timeline_summary(PERFORMANCE_CRITIQUE_STAGE)


def performance_scan_tools_failed(tool_summary: dict[str, Any]) -> tuple[bool, list[str]]:
    assert PERFORMANCE_KIND.tool_names is not None
    return tools_failed(tool_summary, PERFORMANCE_KIND.tool_names)


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
    emit_stub_panel(
        PERFORMANCE_KIND,
        store=store,
        registry=registry,
        critique_router=critique_router,
        run_id=run_id,
        producer_tax_key=producer_tax_key,
        scan_summary=scan_summary,
        block=block,
        scan_failed_fn=performance_scan_tools_failed,
        build_fix=lambda failing: required_fix_artifact(
            failing=failing,
            validation_prefix="resolve performance findings",
            acceptance="ruff_perf and N+1 heuristic pass",
        ),
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
    return execute_llm(
        PERFORMANCE_KIND,
        store=store,
        registry=registry,
        critique_router=critique_router,
        run_id=run_id,
        producer_tax_key=producer_tax_key,
        scan_summary=scan_summary,
        base_url=base_url,
        model_id=model_id,
        block=block,
        response_model=PerformanceCritiqueLlmResponse,
        system_prompt=(
            'Return JSON only: {"verdict":"PASS"|"FAIL","summary":"string"}. '
            "FAIL when ruff_perf or n_plus_one_heuristic report issues."
        ),
        build_user_content=lambda summary, _tf, failing: json.dumps(
            {"tools": summary.get("security_scan_tools"), "failing": failing},
        ),
        scan_failed_fn=performance_scan_tools_failed,
        build_fixes_fn=lambda failing, _parsed: [
            required_fix_artifact(
                failing=failing or ["llm"],
                validation_prefix="resolve performance findings",
                acceptance="ruff_perf and N+1 heuristic pass",
            ),
        ],
        llm_failed_fn=lambda parsed, _tf, _failing: str(parsed.verdict).upper() == "FAIL",
        evidence_ref_fn=lambda _tax_key: "perf://llm",
        timeout_seconds=timeout_seconds,
        unanimous_gate_enforce=unanimous_gate_enforce,
    )
