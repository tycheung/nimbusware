from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from agent_core.models import (
    RequiredFixArtifact,
)
from nimbusware_extensions.phase2 import UniversalCritiqueRouter
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.scan_critique_tools import scan_tools_failed
from nimbusware_orchestrator.scan_stub_critique_emit import (
    ScanStubCritiqueConfig,
    emit_scan_stub_critique_panel,
)
from nimbusware_orchestrator.security_scan import run_security_scan, security_scan_tool_summary
from nimbusware_orchestrator.workflow_scan_critique import (
    SecurityCritiqueBlock,
    scan_critique_gate_timeline_summary,
)
from nimbusware_store.protocol import EventStore

SECURITY_CRITIQUE_STAGE = "implementation.security_critique"
_SECURITY_CRITIC = "security_critic"
_SECURITY_TOOLS = ("ruff", "bandit", "mypy")

_SECURITY_STUB_CONFIG = ScanStubCritiqueConfig(
    stage_name=SECURITY_CRITIQUE_STAGE,
    metadata_key="security_critique",
    specialist_tax_key=_SECURITY_CRITIC,
    evidence_scheme="scan",
    evidence_ok="scan://security_tools_clean",
    mirror_evidence="scan://paired_critic_mirrors_security",
    min_pairing_count=2,
    require_specialist_in_pairing=False,
)


class SecurityCritiqueLlmResponse(BaseModel):
    model_config = {"extra": "ignore"}

    verdict: str = "PASS"
    summary: str = ""
    failing_tools: list[str] = Field(default_factory=list)


def security_critique_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    return scan_critique_gate_timeline_summary(
        events,
        stage_name=SECURITY_CRITIQUE_STAGE,
    )


def security_scan_tools_failed(tool_summary: dict[str, Any]) -> tuple[bool, list[str]]:
    return scan_tools_failed(tool_summary, _SECURITY_TOOLS)


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
    from nimbusware_orchestrator.sql_profiler import run_sql_profiler_summary

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
    failed, failing_tools = security_scan_tools_failed(scan_summary)
    fixes = [_required_fix_for_tools(failing_tools)] if failing_tools else []
    emit_scan_stub_critique_panel(
        store,
        registry,
        critique_router,
        run_id=run_id,
        producer_tax_key=producer_tax_key,
        scan_summary=scan_summary,
        block=block,
        config=_SECURITY_STUB_CONFIG,
        failed=failed,
        failing_items=failing_tools,
        fixes=fixes,
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
    from nimbusware_orchestrator.scan_critique_llm import execute_scan_critique_llm

    tools = scan_summary.get("security_scan_tools") or {}

    def _build_user_content(
        summary: dict[str, Any],
        _tool_failed: bool,
        failing_tools: list[str],
    ) -> str:
        return json.dumps(
            {
                "tools": tools,
                "rules_failed": failing_tools,
                "snippet": summary.get("security_scan_snippet", "")[:1500],
            },
        )

    def _llm_failed(parsed: SecurityCritiqueLlmResponse, _tf: bool, _failing: list[str]) -> bool:
        return str(parsed.verdict).upper() == "FAIL" or bool(parsed.failing_tools)

    def _build_fixes(failing_tools: list[str], parsed: SecurityCritiqueLlmResponse) -> list:
        if str(parsed.verdict).upper() == "FAIL" or bool(parsed.failing_tools):
            return [_required_fix_for_tools(failing_tools or list(parsed.failing_tools))]
        return []

    def _stage_metadata(
        summary: dict[str, Any], parsed: SecurityCritiqueLlmResponse
    ) -> dict[str, Any]:
        return {
            "llm_summary": str(parsed.summary).strip()[:500],
            "scan_summary": summary,
        }

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
        stage_name=SECURITY_CRITIQUE_STAGE,
        metadata_key="security_critique",
        specialist_tax_key=_SECURITY_CRITIC,
        response_model=SecurityCritiqueLlmResponse,
        system_prompt=(
            "You are a security critic for Nimbusware. Return JSON only: "
            '{"verdict":"PASS"|"FAIL","summary":"string","failing_tools":[]}. '
            "FAIL when ruff, bandit, or mypy scans report issues."
        ),
        build_user_content=_build_user_content,
        scan_failed_fn=security_scan_tools_failed,
        build_fixes_fn=_build_fixes,
        llm_failed_fn=_llm_failed,
        build_stage_metadata=_stage_metadata,
        min_pairing_count=2,
        require_specialist_in_pairing=False,
        verdict_mode="uniform",
        timeout_seconds=timeout_seconds,
        unanimous_gate_enforce=unanimous_gate_enforce,
    )
