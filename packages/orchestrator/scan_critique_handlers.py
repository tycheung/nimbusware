from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from agent_core.context_budget import truncate_for_llm_history
from extensions.extension_runtime import UniversalCritiqueRouter
from orchestrator.registry import RoleRegistry
from orchestrator.scan_critique_kinds import (
    NETWORK_KIND,
    PERFORMANCE_KIND,
    SECURITY_KIND,
    NetworkResilienceLlmResponse,
    PerformanceCritiqueLlmResponse,
    ScanCritiqueKind,
    SecurityCritiqueLlmResponse,
    emit_stub_panel,
    execute_llm,
    network_scan_summary_failed,
    required_fix_artifact,
    run_security_scan_summary,
    timeline_summary,
    tools_failed,
)
from orchestrator.workflow_scan_critique import (
    NetworkResilienceCritiqueBlock,
    PerformanceCritiqueBlock,
    SecurityCritiqueBlock,
)
from store.protocol import EventStore

SECURITY_CRITIQUE_STAGE = SECURITY_KIND.stage_name
PERFORMANCE_CRITIQUE_STAGE = PERFORMANCE_KIND.stage_name
NETWORK_RESILIENCE_CRITIQUE_STAGE = NETWORK_KIND.stage_name

security_critique_timeline_summary = timeline_summary(SECURITY_CRITIQUE_STAGE)
performance_critique_timeline_summary = timeline_summary(PERFORMANCE_CRITIQUE_STAGE)
network_resilience_critique_timeline_summary = timeline_summary(NETWORK_RESILIENCE_CRITIQUE_STAGE)
scan_summary_failed = network_scan_summary_failed


@dataclass(frozen=True)
class _ScanHandlerSpec:
    kind: ScanCritiqueKind
    response_model: type[Any]
    system_prompt: str
    validation_prefix: str
    acceptance: str
    scan_failed_fn: Callable[[dict[str, Any]], tuple[bool, list[str]]]
    default_producer: str | None = None
    evidence_ref: str | None = None
    build_user_content: Callable[[dict[str, Any], bool, list[str]], str] | None = None
    build_fixes_fn: Callable[[list[str], Any], list[Any]] | None = None
    llm_failed_fn: Callable[[Any, bool, list[str]], bool] | None = None
    build_stage_metadata: Callable[[dict[str, Any], Any], dict[str, Any]] | None = None


def _tools_failed_for(kind: ScanCritiqueKind) -> Callable[[dict[str, Any]], tuple[bool, list[str]]]:
    assert kind.tool_names is not None

    def _fn(tool_summary: dict[str, Any]) -> tuple[bool, list[str]]:
        return tools_failed(tool_summary, kind.tool_names)  # type: ignore[arg-type]

    return _fn


def _default_build_fixes(validation_prefix: str, acceptance: str, *, tool_key: str = "llm"):
    def _fn(failing: list[str], _parsed: Any) -> list[Any]:
        return [
            required_fix_artifact(
                failing=failing or [tool_key],
                validation_prefix=validation_prefix,
                acceptance=acceptance,
            ),
        ]

    return _fn


def _default_llm_failed(parsed: Any, _tf: bool, _failing: list[str]) -> bool:
    return str(getattr(parsed, "verdict", "PASS")).upper() == "FAIL"


_SECURITY_SPEC = _ScanHandlerSpec(
    kind=SECURITY_KIND,
    response_model=SecurityCritiqueLlmResponse,
    system_prompt=(
        "You are a security critic for Nimbusware. Return JSON only: "
        '{"verdict":"PASS"|"FAIL","summary":"string","failing_tools":[]}. '
        "FAIL when ruff, bandit, or mypy scans report issues."
    ),
    validation_prefix="resolve security scan failures",
    acceptance="ruff, bandit, and mypy exit 0 on workspace",
    scan_failed_fn=_tools_failed_for(SECURITY_KIND),
    build_user_content=lambda summary, _tf, failing: json.dumps(
        {
            "tools": summary.get("security_scan_tools") or {},
            "rules_failed": failing,
            "snippet": summary.get("security_scan_snippet", "")[:1500],
        },
    ),
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
)

_PERFORMANCE_SPEC = _ScanHandlerSpec(
    kind=PERFORMANCE_KIND,
    response_model=PerformanceCritiqueLlmResponse,
    system_prompt=(
        'Return JSON only: {"verdict":"PASS"|"FAIL","summary":"string"}. '
        "FAIL when ruff_perf or n_plus_one_heuristic report issues."
    ),
    validation_prefix="resolve performance findings",
    acceptance="ruff_perf and N+1 heuristic pass",
    scan_failed_fn=_tools_failed_for(PERFORMANCE_KIND),
    build_user_content=lambda summary, _tf, failing: json.dumps(
        {"tools": summary.get("security_scan_tools"), "failing": failing},
    ),
    evidence_ref="perf://llm",
)

_NETWORK_SPEC = _ScanHandlerSpec(
    kind=NETWORK_KIND,
    response_model=NetworkResilienceLlmResponse,
    system_prompt=(
        'Return JSON only: {"verdict":"PASS"|"FAIL","summary":"string"}. '
        "FAIL when HTTP resilience or SQL query budget checks failed."
    ),
    validation_prefix="resolve network/resilience",
    acceptance="HTTP clients use timeouts; SQL query budget respected",
    scan_failed_fn=network_scan_summary_failed,
    default_producer=NETWORK_KIND.default_producer,
    build_user_content=lambda summary, _tf, _failing: truncate_for_llm_history(
        json.dumps(summary),
        max_chars=4000,
    ),
    evidence_ref="net://llm",
)


def _emit_stub(spec: _ScanHandlerSpec, block_type: type[Any]):
    def _panel(
        store: EventStore,
        registry: RoleRegistry,
        critique_router: UniversalCritiqueRouter,
        *,
        run_id: UUID,
        scan_summary: dict[str, Any],
        block: Any,
        unanimous_gate_enforce: bool = False,
        producer_tax_key: str | None = None,
    ) -> None:
        producer = producer_tax_key or spec.default_producer or spec.kind.default_producer
        emit_stub_panel(
            spec.kind,
            store=store,
            registry=registry,
            critique_router=critique_router,
            run_id=run_id,
            producer_tax_key=producer,
            scan_summary=scan_summary,
            block=block,
            scan_failed_fn=spec.scan_failed_fn,
            build_fix=lambda failing: required_fix_artifact(
                failing=failing,
                validation_prefix=spec.validation_prefix,
                acceptance=spec.acceptance,
            ),
            unanimous_gate_enforce=unanimous_gate_enforce,
        )

    _panel.__annotations__["block"] = block_type
    return _panel


def _execute_llm(spec: _ScanHandlerSpec, block_type: type[Any]):
    build_fixes = spec.build_fixes_fn or _default_build_fixes(
        spec.validation_prefix,
        spec.acceptance,
    )
    llm_failed = spec.llm_failed_fn or _default_llm_failed
    assert spec.build_user_content is not None

    def _run(
        store: EventStore,
        registry: RoleRegistry,
        critique_router: UniversalCritiqueRouter,
        *,
        run_id: UUID,
        scan_summary: dict[str, Any],
        base_url: str,
        model_id: str,
        block: Any,
        timeout_seconds: float = 120.0,
        unanimous_gate_enforce: bool = False,
        producer_tax_key: str | None = None,
    ) -> bool:
        producer = producer_tax_key or spec.default_producer or spec.kind.default_producer
        return execute_llm(
            spec.kind,
            store=store,
            registry=registry,
            critique_router=critique_router,
            run_id=run_id,
            producer_tax_key=producer,
            scan_summary=scan_summary,
            base_url=base_url,
            model_id=model_id,
            block=block,
            response_model=spec.response_model,
            system_prompt=spec.system_prompt,
            build_user_content=spec.build_user_content,
            scan_failed_fn=spec.scan_failed_fn,
            build_fixes_fn=build_fixes,
            llm_failed_fn=llm_failed,
            build_stage_metadata=spec.build_stage_metadata,
            evidence_ref_fn=(lambda _tax: spec.evidence_ref) if spec.evidence_ref else None,
            timeout_seconds=timeout_seconds,
            unanimous_gate_enforce=unanimous_gate_enforce,
        )

    _run.__annotations__["block"] = block_type
    return _run


security_scan_tools_failed = _SECURITY_SPEC.scan_failed_fn
performance_scan_tools_failed = _PERFORMANCE_SPEC.scan_failed_fn

emit_stub_security_critique_panel = _emit_stub(_SECURITY_SPEC, SecurityCritiqueBlock)
execute_security_critique_llm = _execute_llm(_SECURITY_SPEC, SecurityCritiqueBlock)
emit_stub_performance_critique_panel = _emit_stub(_PERFORMANCE_SPEC, PerformanceCritiqueBlock)
execute_performance_critique_llm = _execute_llm(_PERFORMANCE_SPEC, PerformanceCritiqueBlock)
emit_stub_network_resilience_critique_panel = _emit_stub(
    _NETWORK_SPEC, NetworkResilienceCritiqueBlock
)
execute_network_resilience_critique_llm = _execute_llm(
    _NETWORK_SPEC, NetworkResilienceCritiqueBlock
)

__all__ = [
    "NETWORK_RESILIENCE_CRITIQUE_STAGE",
    "PERFORMANCE_CRITIQUE_STAGE",
    "SECURITY_CRITIQUE_STAGE",
    "emit_stub_network_resilience_critique_panel",
    "emit_stub_performance_critique_panel",
    "emit_stub_security_critique_panel",
    "execute_network_resilience_critique_llm",
    "execute_performance_critique_llm",
    "execute_security_critique_llm",
    "network_resilience_critique_timeline_summary",
    "performance_critique_timeline_summary",
    "performance_scan_tools_failed",
    "run_security_scan_summary",
    "scan_summary_failed",
    "security_critique_timeline_summary",
    "security_scan_tools_failed",
]
