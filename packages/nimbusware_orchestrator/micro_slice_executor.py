from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from nimbusware_env.env_flags import (
    nimbusware_use_llm_enabled,
)
from nimbusware_orchestrator.llm_slice import execute_slice_replan_llm
from nimbusware_orchestrator.micro_slice import SlicePlan, micro_slice_count_for_run
from nimbusware_orchestrator.micro_slice_plan import (
    custom_agent_system_prompt as _custom_agent_system_prompt,
)
from nimbusware_orchestrator.micro_slice_plan import (
    default_stub_slice_plan,
)
from nimbusware_orchestrator.micro_slice_plan import (
    plan_one_slice as _plan_one_slice,
)
from nimbusware_orchestrator.micro_slice_run_context import (
    micro_slice_effective_from_rows,
    slice_replan_max_for_run,
)
from nimbusware_orchestrator.micro_slice_verify import (
    run_slice_verify_and_test as _run_slice_verify_and_test,
)
from nimbusware_orchestrator.slice_diff import (
    check_slice_diff_budget,
    collect_slice_diff_stats,
    subdivide_slice_plan,
)
from nimbusware_orchestrator.slice_gate import SliceGateChainResult
from nimbusware_orchestrator.slice_implement import execute_slice_implement

if TYPE_CHECKING:
    from nimbusware_orchestrator.pipeline import RunOrchestrator


from nimbusware_orchestrator.micro_slice_executor_context import (
    _emit_slice_stage,
    _resolve_slice_block,
    resolve_slice_block_for_plan,
)
from nimbusware_orchestrator.micro_slice_executor_gate import finish_micro_slice_gate_chain


def execute_single_micro_slice(
    orch: RunOrchestrator,
    run_id: UUID,
    *,
    slice_index: int,
    workspace: Path | None = None,
    plan: SlicePlan | None = None,
    backlog_slice_id: str | None = None,
) -> SliceGateChainResult:
    rows = orch._store.list_run_events(str(run_id))
    from nimbusware_maker.workspace import resolve_run_workspace

    ws = resolve_run_workspace(rows, override=workspace)
    base = orch._base_cfg()
    runtime = base.get("runtime") or {}
    timeout = float(runtime.get("request_timeout_seconds", 120))
    max_replan = slice_replan_max_for_run(rows)

    from nimbusware_orchestrator.autopilot_profiles import autopilot_profile_from_rows
    from nimbusware_orchestrator.diagnose_learn import latest_learning_excerpt_from_rows
    from nimbusware_orchestrator.slice_cycle_integration import (
        maybe_run_repo_explore_slice_stage,
    )
    from nimbusware_orchestrator.slice_interjection import (
        _infer_patch_target_paths,
        apply_interjection_to_plan,
        gate_result_for_force_break,
        gate_result_for_skip_slice,
        handle_build_from_chat_interjection,
        handle_patch_from_chat_interjection,
        handle_skip_slice_interjection,
        process_interjection_cycle,
        steer_excerpt_from_cycle,
    )

    profile = autopilot_profile_from_rows(rows)
    interjection = process_interjection_cycle(orch._store, run_id)
    if interjection.force_break:
        stub = plan or default_stub_slice_plan(slice_index)
        return gate_result_for_force_break(stub)
    if interjection.build_from_chat:
        handle_build_from_chat_interjection(orch, run_id, interjection, rows)
        stub = plan or default_stub_slice_plan(slice_index)
        return gate_result_for_force_break(stub)
    if interjection.skip_slice:
        handle_skip_slice_interjection(orch._store, run_id, interjection, rows)
        stub = plan or default_stub_slice_plan(slice_index)
        return gate_result_for_skip_slice(stub)

    patch_backlog_id: str | None = None
    if interjection.patch_from_chat:
        patch_backlog_id = handle_patch_from_chat_interjection(
            orch._store,
            run_id,
            interjection,
            rows,
        )
    steer_excerpt = steer_excerpt_from_cycle(interjection)

    budget_feedback: str | None = None
    active_plan = plan or _plan_one_slice(
        orch,
        run_id,
        slice_index=slice_index,
        budget_feedback=budget_feedback,
    )
    active_plan = apply_interjection_to_plan(active_plan, interjection)
    effective_backlog_slice_id = backlog_slice_id
    if patch_backlog_id:
        patch_msgs = [i.message for i in interjection.items if i.patch_from_chat]
        active_plan = SlicePlan(
            slice_id=patch_backlog_id,
            target_paths=_infer_patch_target_paths("\n".join(patch_msgs), rows),
            rationale="\n".join(patch_msgs)[:4000] or "Operator patch request",
            acceptance_criteria=active_plan.acceptance_criteria,
        )
        effective_backlog_slice_id = patch_backlog_id
    maybe_run_repo_explore_slice_stage(
        orch._store,
        run_id,
        ws,
        slice_index=slice_index,
    )
    learning_excerpt = latest_learning_excerpt_from_rows(rows)
    replan_attempt = 0
    diff_unified = ""
    stats_source = "plan_estimate"
    duration_ms = 0

    while True:
        block = resolve_slice_block_for_plan(orch, run_id, active_plan)
        orch.record_micro_slice_plan(run_id, active_plan)

        started = time.perf_counter()
        model = orch._selected_model_for_run(run_id)
        impl_result = execute_slice_implement(
            ws,
            active_plan,
            timeout_seconds=timeout,
            llm_base_url=str(runtime.get("base_url", "http://localhost:11434")) if model else None,
            llm_model_id=model,
            llm_system_prompt=_custom_agent_system_prompt(
                orch,
                orch._store.list_run_events(str(run_id)),
            ),
            learning_excerpt=learning_excerpt,
            steer_excerpt=steer_excerpt,
        )
        symbol_sketch = ""
        from nimbusware_env.env_flags import (
            nimbusware_slice_lsp_enabled,
            nimbusware_slice_symbol_sketch_max_chars,
        )

        lsp_reason = ""
        if active_plan.target_paths:
            from nimbusware_orchestrator.slice_lsp_client import (
                build_symbol_sketch_with_lsp_fallback,
            )

            symbol_sketch, lsp_reason = build_symbol_sketch_with_lsp_fallback(
                ws,
                active_plan.target_paths,
                max_chars=nimbusware_slice_symbol_sketch_max_chars(),
                lsp_enabled=nimbusware_slice_lsp_enabled(),
            )
        impl_meta: dict[str, Any] = {
            "slice_id": active_plan.slice_id,
            "slice_implement_mode": impl_result.mode,
            "slice_implement_exit": impl_result.exit_code,
            "paths_touched": list(impl_result.paths_touched),
            "symbol_sketch": symbol_sketch,
        }
        if effective_backlog_slice_id:
            impl_meta["backlog_slice_id"] = effective_backlog_slice_id
        if impl_result.mode == "agent" and impl_result.log.strip():
            impl_meta["agent_tool_log"] = impl_result.log[:8000]
        if lsp_reason:
            impl_meta["symbol_sketch_lsp_reason"] = lsp_reason
        _emit_slice_stage(orch, run_id, "slice.implement", metadata=impl_meta)
        duration_ms = int((time.perf_counter() - started) * 1000)

        stats = collect_slice_diff_stats(ws, active_plan)
        stats_source = stats.source
        diff_unified = stats.unified_diff
        budget = check_slice_diff_budget(stats, block)

        if budget.ok or replan_attempt >= max_replan:
            break

        subdivided = subdivide_slice_plan(
            active_plan,
            budget=budget,
            config=block,
            stats=stats,
            replan_attempt=replan_attempt + 1,
        )
        if subdivided is None and nimbusware_use_llm_enabled():
            model = orch._selected_model_for_run(run_id)
            if model:
                subdivided = execute_slice_replan_llm(
                    rows=orch._store.list_run_events(str(run_id)),
                    base_url=str(runtime.get("base_url", "http://localhost:11434")),
                    model_id=model,
                    prior_plan=active_plan,
                    budget_message=budget.message,
                    replan_attempt=replan_attempt + 1,
                    timeout_seconds=timeout,
                    system_prompt=_custom_agent_system_prompt(
                        orch,
                        orch._store.list_run_events(str(run_id)),
                    ),
                )

        if subdivided is None:
            break

        replan_meta: dict[str, Any] = {
            "slice_id": active_plan.slice_id,
            "next_slice_id": subdivided.slice_id,
            "replan_attempt": replan_attempt + 1,
            "budget_message": budget.message,
            "diff_stats": {
                "file_count": len(stats.changed_files),
                "loc_added": stats.loc_added,
                "loc_removed": stats.loc_removed,
                "source": stats.source,
            },
        }
        ms_eff = micro_slice_effective_from_rows(rows)
        if isinstance(ms_eff, dict) and ms_eff.get("fleet_cap_active"):
            from nimbusware_orchestrator.fleet_slice_caps import fleet_replan_metadata

            replan_meta.update(fleet_replan_metadata(fleet_cap_active=True))
        _emit_slice_stage(
            orch,
            run_id,
            "slice.replan",
            metadata=replan_meta,
        )
        active_plan = subdivided
        budget_feedback = budget.message
        replan_attempt += 1

    gate = finish_micro_slice_gate_chain(
        orch,
        run_id,
        ws=ws,
        rows=rows,
        block=block,
        active_plan=active_plan,
        effective_backlog_slice_id=effective_backlog_slice_id,
        timeout=timeout,
        runtime=runtime,
        duration_ms=duration_ms,
        diff_unified=diff_unified,
        stats_source=stats_source,
        replan_attempt=replan_attempt,
        profile=profile,
    )
    return gate


def execute_micro_slice_pass(
    orch: RunOrchestrator,
    run_id: UUID,
    *,
    workspace: Path | None = None,
) -> list[SliceGateChainResult]:
    rows = orch._store.list_run_events(str(run_id))
    from nimbusware_maker.workspace import resolve_run_workspace

    ws = resolve_run_workspace(rows, override=workspace)
    slice_count = micro_slice_count_for_run(rows)
    results: list[SliceGateChainResult] = []

    for index in range(1, slice_count + 1):
        gate = execute_single_micro_slice(
            orch,
            run_id,
            slice_index=index,
            workspace=workspace,
        )
        results.append(gate)
        if not gate.passed:
            break
    orch.maybe_rebuild_memory_index(run_id)
    from nimbusware_orchestrator.git_outputs import emit_git_finalize_after_micro_slice_pass

    emit_git_finalize_after_micro_slice_pass(
        orch,
        run_id,
        ws,
        results,
        emit_stage=_emit_slice_stage,
    )
    if results and all(r.passed for r in results):
        rows = orch._store.list_run_events(str(run_id))
        orch._emit_bundle_integrator_gate(run_id)
        orch._maybe_emit_integration_adapter_writer_stage(run_id)
        orch._maybe_emit_agent_evaluator_stage(run_id)
        orch._maybe_emit_self_refinement_stage_marker(run_id)
        from nimbusware_orchestrator.enforcement_pipeline import emit_terminal_enforcement_gate

        emit_terminal_enforcement_gate(orch._store, run_id, ws, rows)
    return results


__all__ = [
    "_custom_agent_system_prompt",
    "_emit_slice_stage",
    "_plan_one_slice",
    "_resolve_slice_block",
    "resolve_slice_block_for_plan",
    "_run_slice_verify_and_test",
    "execute_micro_slice_pass",
    "execute_single_micro_slice",
]
