from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from nimbusware_extensions.phase2 import UniversalCritiqueRouter
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.scan_critique_kinds import (
    SECURITY_KIND,
    SecurityCritiqueLlmResponse,
    emit_stub_panel,
    execute_llm,
    required_fix_artifact,
    run_security_scan_summary,
    timeline_summary,
    tools_failed,
)
from nimbusware_orchestrator.workflow_scan_critique import SecurityCritiqueBlock
from nimbusware_store.protocol import EventStore

SECURITY_CRITIQUE_STAGE = SECURITY_KIND.stage_name
security_critique_timeline_summary = timeline_summary(SECURITY_CRITIQUE_STAGE)

__all__ = [
    "SECURITY_CRITIQUE_STAGE",
    "emit_stub_security_critique_panel",
    "execute_security_critique_llm",
    "run_security_scan_summary",
    "security_critique_timeline_summary",
    "security_scan_tools_failed",
]


def security_scan_tools_failed(tool_summary: dict[str, Any]) -> tuple[bool, list[str]]:
    assert SECURITY_KIND.tool_names is not None
    return tools_failed(tool_summary, SECURITY_KIND.tool_names)


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
    emit_stub_panel(
        SECURITY_KIND,
        store=store,
        registry=registry,
        critique_router=critique_router,
        run_id=run_id,
        producer_tax_key=producer_tax_key,
        scan_summary=scan_summary,
        block=block,
        scan_failed_fn=security_scan_tools_failed,
        build_fix=lambda failing: required_fix_artifact(
            failing=failing,
            validation_prefix="resolve security scan failures",
            acceptance="ruff, bandit, and mypy exit 0 on workspace",
        ),
        unanimous_gate_enforce=unanimous_gate_enforce,
    )


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
    tools = scan_summary.get("security_scan_tools") or {}

    return execute_llm(
        SECURITY_KIND,
        store=store,
        registry=registry,
        critique_router=critique_router,
        run_id=run_id,
        producer_tax_key=producer_tax_key,
        scan_summary=scan_summary,
        base_url=base_url,
        model_id=model_id,
        block=block,
        response_model=SecurityCritiqueLlmResponse,
        system_prompt=(
            "You are a security critic for Nimbusware. Return JSON only: "
            '{"verdict":"PASS"|"FAIL","summary":"string","failing_tools":[]}. '
            "FAIL when ruff, bandit, or mypy scans report issues."
        ),
        build_user_content=lambda summary, _tf, failing: json.dumps(
            {
                "tools": tools,
                "rules_failed": failing,
                "snippet": summary.get("security_scan_snippet", "")[:1500],
            },
        ),
        scan_failed_fn=security_scan_tools_failed,
        build_fixes_fn=lambda failing, parsed: (
            [
                required_fix_artifact(
                    failing=failing or list(parsed.failing_tools),
                    validation_prefix="resolve security scan failures",
                    acceptance="ruff, bandit, and mypy exit 0 on workspace",
                ),
            ]
            if str(parsed.verdict).upper() == "FAIL" or bool(parsed.failing_tools)
            else []
        ),
        llm_failed_fn=lambda parsed, _tf, _failing: (
            str(parsed.verdict).upper() == "FAIL" or bool(parsed.failing_tools)
        ),
        build_stage_metadata=lambda summary, parsed: {
            "llm_summary": str(parsed.summary).strip()[:500],
            "scan_summary": summary,
        },
        timeout_seconds=timeout_seconds,
        unanimous_gate_enforce=unanimous_gate_enforce,
    )
