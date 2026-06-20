from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from agent_core.context_budget import truncate_for_llm_history
from agent_core.models import RequiredFixArtifact
from nimbusware_extensions.phase2 import UniversalCritiqueRouter
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.scan_critique_llm import execute_scan_critique_llm
from nimbusware_orchestrator.scan_stub_critique_emit import (
    ScanStubCritiqueConfig,
    emit_scan_stub_critique_panel,
)
from nimbusware_orchestrator.workflow_scan_critique import (
    NetworkResilienceCritiqueBlock,
    scan_critique_gate_timeline_summary,
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
    return execute_scan_critique_llm(
        store,
        registry,
        critique_router,
        run_id=run_id,
        producer_tax_key="backend_writer",
        scan_summary=scan_summary,
        base_url=base_url,
        model_id=model_id,
        block=block,
        stage_name=NETWORK_RESILIENCE_CRITIQUE_STAGE,
        metadata_key="network_resilience_critique",
        specialist_tax_key=_NETWORK_RESILIENCE_CRITIC,
        response_model=NetworkResilienceLlmResponse,
        system_prompt=(
            'Return JSON only: {"verdict":"PASS"|"FAIL","summary":"string"}. '
            "FAIL when HTTP resilience or SQL query budget checks failed."
        ),
        build_user_content=lambda summary, _tf, _failing: truncate_for_llm_history(
            json.dumps(summary),
            max_chars=4000,
        ),
        scan_failed_fn=scan_summary_failed,
        build_fixes_fn=lambda reasons, _parsed: [_required_fix(reasons or ["llm"])],
        llm_failed_fn=lambda parsed, _tf, _failing: str(parsed.verdict).upper() == "FAIL",
        evidence_ref_fn=lambda _tax_key: "net://llm",
        timeout_seconds=timeout_seconds,
        unanimous_gate_enforce=unanimous_gate_enforce,
    )
