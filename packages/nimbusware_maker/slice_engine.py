"""Orchestrator slice execution boundary for Maker.

``slice_workflow`` imports this module only — not ``hermes_orchestrator`` directly.
Lazy helpers wrap optional LLM / scan imports used during approve/apply paths.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes_orchestrator.micro_slice import (
    SlicePlan,
    micro_slice_count_for_run,
    parse_slice_plan,
)
from hermes_orchestrator.micro_slice_executor import (
    _custom_agent_system_prompt,
    _emit_slice_stage,
    _plan_one_slice,
    _resolve_slice_block,
    _run_slice_verify_and_test,
)
from hermes_orchestrator.slice_implement import execute_slice_implement, slice_implement_mode
from hermes_orchestrator.slice_patch_apply import apply_slice_file_edits

__all__ = [
    "SlicePlan",
    "_collect_slice_diff_stats",
    "_complete_slice_p3_evidence",
    "_custom_agent_system_prompt",
    "_emit_slice_stage",
    "_execute_slice_critique_llm",
    "_execute_slice_implement_llm",
    "_plan_one_slice",
    "_resolve_slice_block",
    "_run_slice_verify_and_test",
    "apply_slice_file_edits",
    "check_slice_diff_budget",
    "execute_slice_implement",
    "micro_slice_count_for_run",
    "parse_slice_plan",
    "preview_diff_for_plan",
    "slice_implement_mode",
]


def _execute_slice_implement_llm(
    *,
    plan: SlicePlan,
    workspace: Path,
    base_url: str,
    model_id: str,
    timeout_seconds: float,
    system_prompt: str,
) -> list[dict[str, str]] | None:
    from hermes_orchestrator.llm_slice import execute_slice_implement_llm

    return execute_slice_implement_llm(
        plan=plan,
        workspace=workspace,
        base_url=base_url,
        model_id=model_id,
        timeout_seconds=timeout_seconds,
        system_prompt=system_prompt,
    )


def _execute_slice_critique_llm(
    *,
    plan: SlicePlan,
    base_url: str,
    model_id: str,
    verify_log: str,
    timeout_seconds: float,
) -> list[str]:
    from hermes_orchestrator.llm_slice import execute_slice_critique_llm

    return execute_slice_critique_llm(
        plan=plan,
        base_url=base_url,
        model_id=model_id,
        verify_log=verify_log,
        timeout_seconds=timeout_seconds,
    )


def _collect_slice_diff_stats(workspace: Path, plan: SlicePlan) -> Any:
    from hermes_orchestrator.slice_diff import collect_slice_diff_stats

    return collect_slice_diff_stats(workspace, plan)


def check_slice_diff_budget(stats: Any, block: Any) -> Any:
    from hermes_orchestrator.slice_diff import check_slice_diff_budget

    return check_slice_diff_budget(stats, block)


def _complete_slice_p3_evidence(
    workspace: Path,
    *,
    timeout_seconds: float,
) -> tuple[int, int]:
    from hermes_orchestrator.performance_scan import run_ruff_perf
    from hermes_orchestrator.security_scan import run_security_scan

    sec = run_security_scan(workspace)
    perf_code, _perf_log = run_ruff_perf(workspace, timeout_seconds=timeout_seconds)
    return sec[0], perf_code


def preview_diff_for_plan(workspace: Path, plan: SlicePlan, *, max_chars: int = 12000) -> str:
    """Unified diff or scope summary for slice prepare (scoped/stub/agent)."""
    from nimbusware_maker.slice_preview import preview_note_for_scoped_mode

    stats = _collect_slice_diff_stats(workspace, plan)
    unified = str(stats.unified_diff or "")
    if unified.strip():
        return unified[:max_chars]
    lines = [preview_note_for_scoped_mode(plan.target_paths)]
    for rel in plan.target_paths[:20]:
        norm = str(rel).replace("\\", "/").lstrip("/")
        fp = workspace / norm
        if fp.is_file():
            try:
                lines.append(f"  {norm} ({fp.stat().st_size} bytes)")
            except OSError:
                lines.append(f"  {norm} (unreadable)")
        else:
            lines.append(f"  {norm} (not present yet)")
    if len(plan.target_paths) > 20:
        lines.append(f"  … and {len(plan.target_paths) - 20} more paths")
    return "\n".join(lines)[:max_chars]
