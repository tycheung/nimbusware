from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from agent_core.context_budget import truncate_for_llm_history
from nimbusware_extensions.phase2 import UniversalCritiqueRouter
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.scan_critique_kinds import (
    NETWORK_KIND,
    NetworkResilienceLlmResponse,
    emit_stub_panel,
    execute_llm,
    network_scan_summary_failed,
    required_fix_artifact,
    timeline_summary,
)
from nimbusware_orchestrator.workflow_scan_critique import NetworkResilienceCritiqueBlock
from nimbusware_store.protocol import EventStore

NETWORK_RESILIENCE_CRITIQUE_STAGE = NETWORK_KIND.stage_name
network_resilience_critique_timeline_summary = timeline_summary(NETWORK_RESILIENCE_CRITIQUE_STAGE)
scan_summary_failed = network_scan_summary_failed


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
    emit_stub_panel(
        NETWORK_KIND,
        store=store,
        registry=registry,
        critique_router=critique_router,
        run_id=run_id,
        producer_tax_key=NETWORK_KIND.default_producer,
        scan_summary=scan_summary,
        block=block,
        scan_failed_fn=network_scan_summary_failed,
        build_fix=lambda reasons: required_fix_artifact(
            failing=reasons,
            validation_prefix="resolve network/resilience",
            acceptance="HTTP clients use timeouts; SQL query budget respected",
        ),
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
    return execute_llm(
        NETWORK_KIND,
        store=store,
        registry=registry,
        critique_router=critique_router,
        run_id=run_id,
        producer_tax_key=NETWORK_KIND.default_producer,
        scan_summary=scan_summary,
        base_url=base_url,
        model_id=model_id,
        block=block,
        response_model=NetworkResilienceLlmResponse,
        system_prompt=(
            'Return JSON only: {"verdict":"PASS"|"FAIL","summary":"string"}. '
            "FAIL when HTTP resilience or SQL query budget checks failed."
        ),
        build_user_content=lambda summary, _tf, _failing: truncate_for_llm_history(
            json.dumps(summary),
            max_chars=4000,
        ),
        scan_failed_fn=network_scan_summary_failed,
        build_fixes_fn=lambda reasons, _parsed: [
            required_fix_artifact(
                failing=reasons or ["llm"],
                validation_prefix="resolve network/resilience",
                acceptance="HTTP clients use timeouts; SQL query budget respected",
            ),
        ],
        llm_failed_fn=lambda parsed, _tf, _failing: str(parsed.verdict).upper() == "FAIL",
        evidence_ref_fn=lambda _tax_key: "net://llm",
        timeout_seconds=timeout_seconds,
        unanimous_gate_enforce=unanimous_gate_enforce,
    )
