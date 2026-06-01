from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any
from uuid import UUID

from nimbusware_maker.approval import (
    STAGE_SLICE_APPLIED,
    STAGE_SLICE_PENDING,
    STAGE_WORKSPACE_SNAPSHOT,
    pending_slice_from_rows,
    slice_is_resolved,
)
from nimbusware_maker.slice_engine import (
    SlicePlan,
    _collect_slice_diff_stats,
    _complete_slice_p3_evidence,
    _custom_agent_system_prompt,
    _emit_slice_stage,
    _execute_slice_critique_llm,
    _resolve_slice_block,
    _run_slice_verify_and_test,
    apply_slice_file_edits,
    check_slice_diff_budget,
    execute_slice_implement,
    slice_implement_mode,
)
from nimbusware_maker.slice_workflow._shared import emit_maker_stage, plan_from_pending
from nimbusware_maker.workspace import resolve_run_workspace
from nimbusware_maker.workspace_snapshot import create_workspace_snapshot


def complete_slice_after_implement(
    orch: Any,
    run_id: UUID,
    ws: Path,
    plan: SlicePlan,
    *,
    duration_ms: int = 0,
) -> Any:
    block = _resolve_slice_block(orch, run_id)
    runtime = orch._base_cfg().get("runtime") or {}
    timeout = float(runtime.get("request_timeout_seconds", 120))

    verify_ok, verify_log, tests_passed, test_out = _run_slice_verify_and_test(
        ws,
        plan,
        timeout_seconds=timeout,
    )
    _emit_slice_stage(
        orch,
        run_id,
        "slice.verify",
        metadata={"slice_id": plan.slice_id, "verify_ok": verify_ok},
        duration_ms=duration_ms,
    )

    critique_verdicts = ["PASS"]
    critique_meta: dict[str, Any] = {"slice_id": plan.slice_id}
    if os.environ.get("HERMES_SLICE_P3_EVIDENCE", "1").lower() not in ("0", "false", "no"):
        sec_exit, perf_exit = _complete_slice_p3_evidence(ws, timeout_seconds=timeout)
        critique_meta["phase3_evidence"] = {
            "security_scan_exit": sec_exit,
            "performance_scan_exit": perf_exit,
        }
        if sec_exit != 0 or perf_exit != 0:
            critique_verdicts = ["FAIL"]
    if os.environ.get("HERMES_USE_LLM", "").lower() in ("1", "true", "yes"):
        model = orch._selected_model_for_run(run_id)
        if model:
            critique_verdicts = _execute_slice_critique_llm(
                plan=plan,
                base_url=str(runtime.get("base_url", "http://localhost:11434")),
                model_id=model,
                verify_log=verify_log,
                timeout_seconds=timeout,
            )
    critique_meta["critique_verdicts"] = critique_verdicts
    _emit_slice_stage(orch, run_id, "slice.critique", metadata=critique_meta, duration_ms=0)
    _emit_slice_stage(
        orch,
        run_id,
        "slice.test",
        metadata={"slice_id": plan.slice_id, "tests_passed": tests_passed},
        duration_ms=0,
    )

    final_stats = _collect_slice_diff_stats(ws, plan)
    final_budget = check_slice_diff_budget(final_stats, block)
    if not final_budget.ok:
        verify_ok = False
    diff_for_gate = final_stats.unified_diff

    gate = orch.record_micro_slice_gate(
        run_id,
        plan,
        verify_ok=verify_ok,
        critique_verdicts=critique_verdicts,
        tests_passed=tests_passed,
        diff_unified=diff_for_gate[:8000],
        test_output=test_out[:4000],
    )
    orch.maybe_rebuild_memory_index(run_id)
    return gate


def apply_pending_slice(orch: Any, run_id: UUID, slice_id: str) -> dict[str, Any]:
    rows = orch._store.list_run_events(str(run_id))
    pending = pending_slice_from_rows(rows)
    if pending is None:
        raise ValueError("no pending slice awaiting approval")
    if str(pending.get("slice_id")) != slice_id:
        raise ValueError(f"pending slice is {pending.get('slice_id')!r}, not {slice_id!r}")
    if slice_is_resolved(rows, slice_id):
        raise ValueError(f"slice already resolved: {slice_id}")

    plan = plan_from_pending(pending)
    ws = resolve_run_workspace(rows)
    snapshot = create_workspace_snapshot(
        ws,
        run_id=str(run_id),
        label=slice_id,
        paths=plan.target_paths,
    )
    emit_maker_stage(
        orch,
        run_id,
        STAGE_WORKSPACE_SNAPSHOT,
        {"slice_id": slice_id, "workspace_snapshot": snapshot},
    )

    started = time.perf_counter()
    runtime = orch._base_cfg().get("runtime") or {}
    timeout = float(runtime.get("request_timeout_seconds", 120))
    model = orch._selected_model_for_run(run_id)
    mode = str(pending.get("implement_mode") or slice_implement_mode())

    if mode == "agent":
        from hermes_agent_tools.runtime import execute_slice_implement_agent

        impl_result = execute_slice_implement_agent(
            ws,
            plan,
            timeout_seconds=timeout,
            llm_base_url=str(runtime.get("base_url", "http://localhost:11434")) if model else None,
            llm_model_id=model,
            llm_system_prompt=_custom_agent_system_prompt(orch, rows),
        )
        impl_meta = {
            "slice_id": plan.slice_id,
            "slice_implement_mode": impl_result.mode,
            "paths_touched": list(impl_result.paths_touched),
        }
    elif mode == "llm":
        edits = pending.get("proposed_edits")
        if isinstance(edits, list) and edits:
            touched, errors = apply_slice_file_edits(ws, plan, edits)
            impl_meta = {
                "slice_id": plan.slice_id,
                "slice_implement_mode": "llm",
                "paths_touched": touched,
                "errors": errors,
            }
        else:
            impl_result = execute_slice_implement(
                ws,
                plan,
                timeout_seconds=timeout,
                llm_base_url=(
                    str(runtime.get("base_url", "http://localhost:11434")) if model else None
                ),
                llm_model_id=model,
                llm_system_prompt=_custom_agent_system_prompt(orch, rows),
            )
            impl_meta = {
                "slice_id": plan.slice_id,
                "slice_implement_mode": impl_result.mode,
                "paths_touched": list(impl_result.paths_touched),
            }
    else:
        impl_result = execute_slice_implement(
            ws,
            plan,
            timeout_seconds=timeout,
            llm_base_url=(
                str(runtime.get("base_url", "http://localhost:11434")) if model else None
            ),
            llm_model_id=model,
            llm_system_prompt=_custom_agent_system_prompt(orch, rows),
        )
        impl_meta = {
            "slice_id": plan.slice_id,
            "slice_implement_mode": impl_result.mode,
            "paths_touched": list(impl_result.paths_touched),
        }

    _emit_slice_stage(orch, run_id, "slice.implement", metadata=impl_meta)
    duration_ms = int((time.perf_counter() - started) * 1000)

    pending_resolved = dict(pending)
    pending_resolved["awaiting_approval"] = False
    emit_maker_stage(orch, run_id, STAGE_SLICE_PENDING, pending_resolved)

    gate = complete_slice_after_implement(orch, run_id, ws, plan, duration_ms=duration_ms)
    emit_maker_stage(
        orch,
        run_id,
        STAGE_SLICE_APPLIED,
        {
            "slice_id": slice_id,
            "workspace_snapshot": snapshot,
            "gate_passed": gate.passed,
        },
    )
    return {
        "status": "applied",
        "slice_id": slice_id,
        "gate_passed": gate.passed,
        "snapshot_id": snapshot.get("snapshot_id"),
    }
