from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    StagePassedEvent,
    StagePassedPayload,
    StageStartedEvent,
    StageStartedPayload,
)
from nimbusware_maker.slice_engine import (
    SlicePlan,
    _collect_slice_diff_stats,
    _complete_slice_p3_evidence,
    _custom_agent_system_prompt,
    _emit_slice_stage,
    _execute_slice_critique_llm,
    _execute_slice_implement_llm,
    _plan_one_slice,
    _resolve_slice_block,
    _run_slice_verify_and_test,
    apply_slice_file_edits,
    check_slice_diff_budget,
    execute_slice_implement,
    micro_slice_count_for_run,
    parse_slice_plan,
    slice_implement_mode,
)
from nimbusware_maker.approval import (
    STAGE_PLAN_APPROVED,
    STAGE_SLICE_APPLIED,
    STAGE_SLICE_PENDING,
    STAGE_SLICE_SKIPPED,
    STAGE_WORKSPACE_REVERTED,
    STAGE_WORKSPACE_SNAPSHOT,
    has_plan_approved,
    last_approved_snapshot_from_rows,
    pending_slice_from_rows,
    slice_is_resolved,
)
from nimbusware_maker.slice_preview import preview_note_for_scoped_mode, unified_diff_from_edits
from nimbusware_maker.workspace import resolve_run_workspace
from nimbusware_maker.workspace_snapshot import (
    create_workspace_snapshot,
    restore_workspace_snapshot,
)


def _emit_maker_stage(
    orch: Any,
    run_id: UUID,
    stage_name: str,
    metadata: dict[str, Any],
) -> None:
    meta = {**metadata, "maker_approval": True}
    now = datetime.now(timezone.utc)
    orch._store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=now,
            metadata=meta,
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    orch._store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata=meta,
            payload=StagePassedPayload(stage_name=stage_name, duration_ms=0),
        ),
    )


def approve_run_plan(orch: Any, run_id: UUID) -> dict[str, Any]:
    rows = orch._store.list_run_events(str(run_id))
    if not rows:
        raise ValueError("run not found")
    if has_plan_approved(rows):
        return {"status": "already_approved"}
    _emit_maker_stage(orch, run_id, STAGE_PLAN_APPROVED, {"approved": True})
    return {"status": "plan_approved"}


def _completed_slice_count(rows: list[dict[str, Any]]) -> int:
    count = 0
    seen: set[str] = set()
    for row in rows:
        if row.get("event_type") != EventType.STAGE_PASSED.value:
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        if payload.get("stage_name") != "slice.gate":
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        if meta.get("slice_gate_verdict") != "PASS":
            continue
        sid = str(meta.get("slice_id") or "")
        if sid and sid not in seen:
            seen.add(sid)
            count += 1
    return count


def prepare_next_pending_slice(orch: Any, run_id: UUID) -> dict[str, Any]:
    rows = orch._store.list_run_events(str(run_id))
    if not rows:
        raise ValueError("run not found")
    if not has_plan_approved(rows):
        raise ValueError("plan not approved — call POST /maker/plan/approve first")

    existing = pending_slice_from_rows(rows)
    if existing is not None:
        return {"status": "awaiting_approval", "pending": existing}

    completed = _completed_slice_count(rows)
    total = micro_slice_count_for_run()
    if completed >= total:
        return {"status": "all_slices_done", "slices_completed": completed, "slice_total": total}

    slice_index = completed + 1
    plan = _plan_one_slice(orch, run_id, slice_index=slice_index)
    orch.record_micro_slice_plan(run_id, plan)

    ws = resolve_run_workspace(rows)
    mode = slice_implement_mode()
    proposed_edits: list[dict[str, str]] | None = None
    diff_unified = ""
    runtime = orch._base_cfg().get("runtime") or {}
    timeout = float(runtime.get("request_timeout_seconds", 120))
    model = orch._selected_model_for_run(run_id)

    if mode == "llm" and model:
        proposed_edits = _execute_slice_implement_llm(
            plan=plan,
            workspace=ws,
            base_url=str(runtime.get("base_url", "http://localhost:11434")),
            model_id=model,
            timeout_seconds=timeout,
            system_prompt=_custom_agent_system_prompt(orch, rows),
        )
        if proposed_edits:
            diff_unified = unified_diff_from_edits(ws, proposed_edits)
    if not diff_unified:
        diff_unified = preview_note_for_scoped_mode(plan.target_paths)

    pending_meta = {
        "slice_id": plan.slice_id,
        "awaiting_approval": True,
        "diff_unified": diff_unified[:12000],
        "implement_mode": mode,
        "rationale": plan.rationale,
        "target_paths": list(plan.target_paths),
        "slice_plan": {
            "slice_id": plan.slice_id,
            "rationale": plan.rationale,
            "target_paths": list(plan.target_paths),
            "acceptance_criteria": plan.acceptance_criteria,
        },
        "proposed_edits": proposed_edits,
        "slice_index": slice_index,
        "slice_total": total,
    }
    _emit_maker_stage(orch, run_id, STAGE_SLICE_PENDING, pending_meta)
    return {
        "status": "awaiting_approval",
        "pending": {
            "slice_id": plan.slice_id,
            "diff_unified": pending_meta["diff_unified"],
            "implement_mode": mode,
            "rationale": plan.rationale,
            "target_paths": list(plan.target_paths),
            "slice_index": slice_index,
            "slice_total": total,
        },
    }


def _plan_from_pending(pending: dict[str, Any]) -> SlicePlan:
    raw = pending.get("slice_plan")
    if isinstance(raw, dict):
        return parse_slice_plan(raw)
    return parse_slice_plan(
        {
            "slice_id": pending.get("slice_id", "slice-1"),
            "rationale": pending.get("rationale", ""),
            "target_paths": pending.get("target_paths") or [],
            "acceptance_criteria": "",
        },
    )


def _complete_slice_after_implement(
    orch: Any,
    run_id: UUID,
    ws: Path,
    plan: SlicePlan,
    *,
    duration_ms: int = 0,
) -> Any:
    import os

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

    plan = _plan_from_pending(pending)
    ws = resolve_run_workspace(rows)
    snapshot = create_workspace_snapshot(
        ws,
        run_id=str(run_id),
        label=slice_id,
        paths=plan.target_paths,
    )
    _emit_maker_stage(
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
    _emit_maker_stage(orch, run_id, STAGE_SLICE_PENDING, pending_resolved)

    gate = _complete_slice_after_implement(orch, run_id, ws, plan, duration_ms=duration_ms)
    _emit_maker_stage(
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


def skip_pending_slice(orch: Any, run_id: UUID, slice_id: str) -> dict[str, Any]:
    rows = orch._store.list_run_events(str(run_id))
    pending = pending_slice_from_rows(rows)
    if pending is None:
        raise ValueError("no pending slice awaiting approval")
    if str(pending.get("slice_id")) != slice_id:
        raise ValueError(f"pending slice is {pending.get('slice_id')!r}, not {slice_id!r}")

    resolved = dict(pending)
    resolved["awaiting_approval"] = False
    _emit_maker_stage(orch, run_id, STAGE_SLICE_PENDING, resolved)
    _emit_maker_stage(orch, run_id, STAGE_SLICE_SKIPPED, {"slice_id": slice_id})
    return {"status": "skipped", "slice_id": slice_id}


def revert_workspace(orch: Any, run_id: UUID) -> dict[str, Any]:
    rows = orch._store.list_run_events(str(run_id))
    snapshot = last_approved_snapshot_from_rows(rows)
    if snapshot is None:
        raise ValueError("no approved workspace snapshot to revert to")
    ws = resolve_run_workspace(rows)
    restored = restore_workspace_snapshot(ws, snapshot)
    _emit_maker_stage(
        orch,
        run_id,
        STAGE_WORKSPACE_REVERTED,
        {
            "workspace_snapshot": snapshot,
            "paths_restored": restored,
        },
    )
    return {
        "status": "reverted",
        "snapshot_id": snapshot.get("snapshot_id"),
        "paths_restored": restored,
    }


def get_pending_state(orch: Any, run_id: UUID) -> dict[str, Any]:
    rows = orch._store.list_run_events(str(run_id))
    if not rows:
        raise ValueError("run not found")
    return {
        "plan_approved": has_plan_approved(rows),
        "pending": pending_slice_from_rows(rows),
        "last_snapshot": last_approved_snapshot_from_rows(rows),
        "awaiting_approval": pending_slice_from_rows(rows) is not None,
    }
