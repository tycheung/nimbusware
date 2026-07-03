from __future__ import annotations

from typing import Any
from uuid import UUID

from maker.approval import (
    STAGE_PLAN_APPROVED,
    STAGE_SLICE_PENDING,
    has_plan_approved,
    last_approved_snapshot_from_rows,
    pending_slice_from_rows,
)
from maker.slice_engine import (
    _custom_agent_system_prompt,
    _execute_slice_implement_llm,
    _plan_one_slice,
    micro_slice_count_for_run,
    preview_diff_for_plan,
    slice_implement_mode,
)
from maker.slice_preview import unified_diff_from_edits
from maker.slice_workflow._shared import completed_slice_count, emit_maker_stage
from maker.workspace import resolve_run_workspace


def approve_run_plan(orch: Any, run_id: UUID) -> dict[str, Any]:
    rows = orch._store.list_run_events(str(run_id))
    if not rows:
        raise ValueError("run not found")
    if has_plan_approved(rows):
        return {"status": "already_approved"}
    emit_maker_stage(orch, run_id, STAGE_PLAN_APPROVED, {"approved": True})
    return {"status": "plan_approved"}


def prepare_next_pending_slice(orch: Any, run_id: UUID) -> dict[str, Any]:
    rows = orch._store.list_run_events(str(run_id))
    if not rows:
        raise ValueError("run not found")
    if not has_plan_approved(rows):
        raise ValueError("plan not approved — call POST /maker/plan/approve first")

    existing = pending_slice_from_rows(rows)
    if existing is not None:
        return {"status": "awaiting_approval", "pending": existing}

    completed = completed_slice_count(rows)
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
        diff_unified = preview_diff_for_plan(ws, plan)

    symbol_sketch = ""
    from env.env_flags import (
        nimbusware_slice_lsp_enabled,
        nimbusware_slice_symbol_sketch_max_chars,
    )

    if plan.target_paths:
        from orchestrator.slice_lsp_client import build_symbol_sketch_with_lsp_fallback

        symbol_sketch, _ = build_symbol_sketch_with_lsp_fallback(
            ws,
            plan.target_paths,
            max_chars=nimbusware_slice_symbol_sketch_max_chars(),
            lsp_enabled=nimbusware_slice_lsp_enabled(),
        )

    pending_meta = {
        "slice_id": plan.slice_id,
        "awaiting_approval": True,
        "diff_unified": diff_unified[:12000],
        "implement_mode": mode,
        "symbol_sketch": symbol_sketch,
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
    emit_maker_stage(orch, run_id, STAGE_SLICE_PENDING, pending_meta)
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
