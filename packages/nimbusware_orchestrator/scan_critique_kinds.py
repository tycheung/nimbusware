from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, Field

from agent_core.models import RequiredFixArtifact
from nimbusware_extensions.extension_runtime import UniversalCritiqueRouter
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.scan_critique_llm import execute_scan_critique_llm
from nimbusware_orchestrator.scan_critique_tools import scan_tools_failed
from nimbusware_orchestrator.scan_stub_critique_emit import (
    ScanStubCritiqueConfig,
    emit_scan_stub_critique_panel,
)
from nimbusware_orchestrator.workflow_scan_critique import scan_critique_gate_timeline_summary
from nimbusware_store.protocol import EventStore

TBlock = TypeVar("TBlock")
TResponse = TypeVar("TResponse", bound=BaseModel)


@dataclass(frozen=True)
class ScanCritiqueKind:
    stage_name: str
    critic_key: str
    metadata_key: str
    tool_names: tuple[str, ...] | None
    stub_config: ScanStubCritiqueConfig
    default_producer: str = "backend_writer"
    min_pairing_count: int = 0
    require_specialist_in_pairing: bool = True
    verdict_mode: Literal["mirror", "uniform", "default"] = "default"


def timeline_summary(stage_name: str) -> Callable[[list[dict[str, Any]]], dict[str, Any] | None]:
    def _fn(events: list[dict[str, Any]]) -> dict[str, Any] | None:
        return scan_critique_gate_timeline_summary(events, stage_name=stage_name)

    return _fn


def tools_failed(
    tool_summary: dict[str, Any],
    tool_names: tuple[str, ...],
) -> tuple[bool, list[str]]:
    return scan_tools_failed(tool_summary, tool_names)


def required_fix_artifact(
    *,
    failing: list[str],
    validation_prefix: str,
    acceptance: str,
) -> RequiredFixArtifact:
    return RequiredFixArtifact.model_validate(
        {
            "artifact_schema_version": 1,
            "format": "json_patch",
            "target_files": ["packages/"],
            "patch_artifact": "[]",
            "validation_steps": [f"{validation_prefix}: {', '.join(failing)}"],
            "acceptance_criteria": acceptance,
        },
    )


def emit_stub_panel(
    kind: ScanCritiqueKind,
    *,
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    run_id: Any,
    producer_tax_key: str,
    scan_summary: dict[str, Any],
    block: Any,
    scan_failed_fn: Callable[[dict[str, Any]], tuple[bool, list[str]]],
    build_fix: Callable[[list[str]], RequiredFixArtifact],
    unanimous_gate_enforce: bool = False,
) -> None:
    failed, failing = scan_failed_fn(scan_summary)
    fixes = [build_fix(failing)] if failing else []
    emit_scan_stub_critique_panel(
        store,
        registry,
        critique_router,
        run_id=run_id,
        producer_tax_key=producer_tax_key,
        scan_summary=scan_summary,
        block=block,
        config=kind.stub_config,
        failed=failed,
        failing_items=failing,
        fixes=fixes,
        unanimous_gate_enforce=unanimous_gate_enforce,
    )


def execute_llm(
    kind: ScanCritiqueKind,
    *,
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    run_id: Any,
    producer_tax_key: str,
    scan_summary: dict[str, Any],
    base_url: str,
    model_id: str,
    block: Any,
    response_model: type[TResponse],
    system_prompt: str,
    build_user_content: Callable[[Mapping[str, Any], bool, list[str]], str],
    scan_failed_fn: Callable[[dict[str, Any]], tuple[bool, list[str]]],
    build_fixes_fn: Callable[[list[str], TResponse], list[Any]],
    llm_failed_fn: Callable[[TResponse, bool, list[str]], bool],
    build_stage_metadata: Callable[[Mapping[str, Any], TResponse], dict[str, Any]] | None = None,
    evidence_ref_fn: Callable[[str], str] | None = None,
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
        stage_name=kind.stage_name,
        metadata_key=kind.metadata_key,
        specialist_tax_key=kind.critic_key,
        response_model=response_model,
        system_prompt=system_prompt,
        build_user_content=build_user_content,
        scan_failed_fn=scan_failed_fn,
        build_fixes_fn=build_fixes_fn,
        llm_failed_fn=llm_failed_fn,
        build_stage_metadata=build_stage_metadata,
        evidence_ref_fn=evidence_ref_fn,
        min_pairing_count=kind.min_pairing_count,
        require_specialist_in_pairing=kind.require_specialist_in_pairing,
        verdict_mode=("mirror" if kind.verdict_mode == "default" else kind.verdict_mode),
        timeout_seconds=timeout_seconds,
        unanimous_gate_enforce=unanimous_gate_enforce,
    )


SECURITY_KIND = ScanCritiqueKind(
    stage_name="implementation.security_critique",
    critic_key="security_critic",
    metadata_key="security_critique",
    tool_names=("ruff", "bandit", "mypy"),
    stub_config=ScanStubCritiqueConfig(
        stage_name="implementation.security_critique",
        metadata_key="security_critique",
        specialist_tax_key="security_critic",
        evidence_scheme="scan",
        evidence_ok="scan://security_tools_clean",
        mirror_evidence="scan://paired_critic_mirrors_security",
        min_pairing_count=2,
        require_specialist_in_pairing=False,
    ),
    min_pairing_count=2,
    require_specialist_in_pairing=False,
    verdict_mode="uniform",
)

PERFORMANCE_KIND = ScanCritiqueKind(
    stage_name="implementation.performance_critique",
    critic_key="performance_critic",
    metadata_key="performance_critique",
    tool_names=("ruff_perf", "n_plus_one_heuristic", "sql_profiler"),
    stub_config=ScanStubCritiqueConfig(
        stage_name="implementation.performance_critique",
        metadata_key="performance_critique",
        specialist_tax_key="performance_critic",
        evidence_scheme="perf",
        evidence_ok="perf://clean",
        mirror_evidence="perf://paired_mirror",
    ),
)

NETWORK_KIND = ScanCritiqueKind(
    stage_name="implementation.network_resilience_critique",
    critic_key="network_resilience_critic",
    metadata_key="network_resilience_critique",
    tool_names=None,
    stub_config=ScanStubCritiqueConfig(
        stage_name="implementation.network_resilience_critique",
        metadata_key="network_resilience_critique",
        specialist_tax_key="network_resilience_critic",
        evidence_scheme="net",
        evidence_ok="net://ok",
        mirror_evidence="net://paired_mirror",
        metadata_scan_field="scan",
    ),
)


class SecurityCritiqueLlmResponse(BaseModel):
    model_config = {"extra": "ignore"}

    verdict: str = "PASS"
    summary: str = ""
    failing_tools: list[str] = Field(default_factory=list)


class PerformanceCritiqueLlmResponse(BaseModel):
    model_config = {"extra": "ignore"}

    verdict: str = "PASS"
    summary: str = ""


class NetworkResilienceLlmResponse(BaseModel):
    model_config = {"extra": "ignore"}

    verdict: str = "PASS"
    summary: str = ""


def network_scan_summary_failed(scan_summary: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if int(scan_summary.get("http_resilience_exit", 0)) != 0:
        reasons.append("http_resilience")
    if int(scan_summary.get("sql_query_budget_exit", 0)) != 0:
        reasons.append("sql_query_budget")
    return bool(reasons), reasons


def run_security_scan_summary(workspace: Path) -> dict[str, Any]:
    from nimbusware_orchestrator.security_scan import run_security_scan, security_scan_tool_summary
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
