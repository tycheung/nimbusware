"""Automatic micro-slice stage execution."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    StagePassedEvent,
    StagePassedPayload,
    StageStartedEvent,
    StageStartedPayload,
)
from hermes_orchestrator.llm_slice import (
    execute_slice_critique_llm,
    execute_slice_plan_llm,
    execute_slice_replan_llm,
)
from hermes_orchestrator.micro_slice import SlicePlan, micro_slice_count_for_run, parse_slice_plan
from hermes_orchestrator.slice_diff import (
    check_slice_diff_budget,
    collect_slice_diff_stats,
    slice_replan_max_attempts,
    subdivide_slice_plan,
)
from hermes_orchestrator.slice_gate import SliceGateChainResult, map_paths_to_test_targets
from hermes_orchestrator.slice_implement import execute_slice_implement
from hermes_orchestrator.verifiers import run_pytest_targets, run_ruff_on_paths
from hermes_orchestrator.workflow_micro_slice import MicroSliceWorkflowBlock
from nimbusware_env.env_flags import (
    hermes_slice_p3_evidence_enabled,
    hermes_use_llm_enabled,
)

if TYPE_CHECKING:
    from hermes_orchestrator.pipeline import RunOrchestrator


def micro_slice_effective_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in rows:
        if row.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = row.get("metadata")
        if isinstance(meta, dict):
            ms = meta.get("micro_slice_effective")
            if isinstance(ms, dict) and ms.get("enabled"):
                return ms
        break
    return None


def default_stub_slice_plan(slice_index: int) -> SlicePlan:
    return parse_slice_plan(
        {
            "slice_id": f"slice-{slice_index}",
            "rationale": "Conservative default micro-slice for automated verify pass",
            "target_paths": [
                "packages/hermes_orchestrator/micro_slice.py",
                "packages/hermes_orchestrator/slice_gate.py",
            ],
            "acceptance_criteria": "Scoped unit tests pass",
        },
    )


def _resolve_slice_block(orch: RunOrchestrator, run_id: UUID) -> MicroSliceWorkflowBlock:
    from hermes_orchestrator.integrator_gate import workflow_profile_from_run_created_rows
    from hermes_orchestrator.workflow_micro_slice import parse_micro_slice_workflow_block

    rows = orch._store.list_run_events(str(run_id))
    wf = workflow_profile_from_run_created_rows(rows)
    block = parse_micro_slice_workflow_block(
        orch.repo_root,
        wf or "micro_slice",
        config_materializer=orch.config_materializer,
    )
    ms = micro_slice_effective_from_rows(rows)
    if not isinstance(ms, dict) or not ms.get("enabled"):
        return block
    return MicroSliceWorkflowBlock(
        enabled=True,
        max_files=int(ms.get("max_files", block.max_files)),
        max_loc=int(ms.get("max_loc", block.max_loc)),
        allowed_globs=block.allowed_globs,
        e2e_enabled=bool(ms.get("e2e_enabled", block.e2e_enabled)),
        e2e_command=block.e2e_command,
    )


def slice_replan_max_for_run(rows: list[dict[str, Any]]) -> int:
    ms = micro_slice_effective_from_rows(rows)
    if isinstance(ms, dict) and "replan_max" in ms:
        return max(0, min(10, int(ms["replan_max"])))
    return slice_replan_max_attempts()


def _custom_agent_system_prompt(orch: RunOrchestrator, rows: list[dict[str, Any]]) -> str | None:
    from nimbusware_config.persist import load_custom_agent_registry

    for row in rows:
        if row.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            break
        agent = meta.get("custom_agent")
        if isinstance(agent, dict) and agent.get("id"):
            reg = load_custom_agent_registry(
                orch.repo_root,
                materializer=orch.config_materializer,
            )
            full = reg.get(str(agent["id"]))
            if full is not None:
                return full.system_prompt
        break
    return None


def _plan_one_slice(
    orch: RunOrchestrator,
    run_id: UUID,
    *,
    slice_index: int,
    budget_feedback: str | None = None,
) -> SlicePlan:
    rows = orch._store.list_run_events(str(run_id))
    use_llm = hermes_use_llm_enabled()
    memory_excerpt = ""
    run_meta = orch._run_created_metadata(run_id)
    from hermes_orchestrator.workflow_memory import (
        memory_settings_from_run_metadata,
        retrieve_memory_excerpt_for_slice,
        run_memory_retrieval_enabled,
    )

    if run_memory_retrieval_enabled(run_meta) and orch._memory_chunk_store is not None:
        settings = memory_settings_from_run_metadata(run_meta)
        stub = default_stub_slice_plan(slice_index)
        memory_excerpt, _, _ = retrieve_memory_excerpt_for_slice(
            orch._memory_chunk_store,
            stub,
            repo_root=orch.repo_root,
            settings=settings,
        )
    if use_llm:
        base = orch._base_cfg()
        runtime = base.get("runtime") or {}
        model = orch._selected_model_for_run(run_id)
        if model:
            plan = execute_slice_plan_llm(
                rows=rows,
                base_url=str(runtime.get("base_url", "http://localhost:11434")),
                model_id=model,
                slice_index=slice_index,
                timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                system_prompt=_custom_agent_system_prompt(orch, rows),
                budget_feedback=budget_feedback,
                memory_excerpt=memory_excerpt,
            )
            if plan is not None:
                return plan
    return default_stub_slice_plan(slice_index)


def _emit_slice_stage(
    orch: RunOrchestrator,
    run_id: UUID,
    stage_name: str,
    *,
    metadata: dict[str, Any] | None = None,
    duration_ms: int = 0,
) -> None:
    now = datetime.now(timezone.utc)
    orch._store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=now,
            metadata=metadata or {},
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    orch._store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata=metadata or {},
            payload=StagePassedPayload(stage_name=stage_name, duration_ms=duration_ms),
        ),
    )


def _run_slice_verify_and_test(
    workspace: Path,
    plan: SlicePlan,
    *,
    timeout_seconds: float,
) -> tuple[bool, str, bool, str]:
    """Verify (ruff + path existence) and scoped pytest for one slice."""
    missing = [p for p in plan.target_paths if not (workspace / p).is_file()]
    sections: list[str] = []
    verify_ok = True
    if missing:
        verify_ok = False
        sections.append(f"missing target files: {missing}")
    ruff_code, ruff_out = run_ruff_on_paths(
        workspace,
        list(plan.target_paths),
        timeout_seconds=timeout_seconds,
    )
    sections.append(f"=== ruff (exit {ruff_code}) ===\n{ruff_out}")
    if ruff_code != 0:
        verify_ok = False
    test_targets = map_paths_to_test_targets(plan.target_paths)
    existing_tests = [t for t in test_targets if (workspace / t).is_file()]
    if existing_tests:
        test_code, test_out = run_pytest_targets(
            workspace,
            existing_tests,
            timeout_seconds=timeout_seconds,
        )
        tests_passed = test_code == 0
    else:
        test_code, test_out = 0, "no mapped test files; skipped\n"
        tests_passed = True
    sections.append(f"=== pytest (exit {test_code}) ===\n{test_out}")
    return verify_ok, "\n".join(sections), tests_passed, test_out


def execute_micro_slice_pass(
    orch: RunOrchestrator,
    run_id: UUID,
    *,
    workspace: Path | None = None,
) -> list[SliceGateChainResult]:
    """Run slice.plan → implement → verify → critique → test → gate for N slices."""
    rows = orch._store.list_run_events(str(run_id))
    from nimbusware_maker.workspace import resolve_run_workspace

    ws = resolve_run_workspace(rows, override=workspace)
    block = _resolve_slice_block(orch, run_id)
    base = orch._base_cfg()
    runtime = base.get("runtime") or {}
    timeout = float(runtime.get("request_timeout_seconds", 120))
    slice_count = micro_slice_count_for_run(rows)
    results: list[SliceGateChainResult] = []

    max_replan = slice_replan_max_for_run(rows)

    for index in range(1, slice_count + 1):
        budget_feedback: str | None = None
        plan = _plan_one_slice(orch, run_id, slice_index=index, budget_feedback=budget_feedback)
        replan_attempt = 0
        diff_unified = ""
        stats_source = "plan_estimate"

        while True:
            orch.record_micro_slice_plan(run_id, plan)

            started = time.perf_counter()
            model = orch._selected_model_for_run(run_id)
            impl_result = execute_slice_implement(
                ws,
                plan,
                timeout_seconds=timeout,
                llm_base_url=str(runtime.get("base_url", "http://localhost:11434"))
                if model
                else None,
                llm_model_id=model,
                llm_system_prompt=_custom_agent_system_prompt(
                    orch,
                    orch._store.list_run_events(str(run_id)),
                ),
            )
            impl_meta = {
                "slice_id": plan.slice_id,
                "slice_implement_mode": impl_result.mode,
                "slice_implement_exit": impl_result.exit_code,
                "paths_touched": list(impl_result.paths_touched),
            }
            _emit_slice_stage(orch, run_id, "slice.implement", metadata=impl_meta)
            duration_ms = int((time.perf_counter() - started) * 1000)

            stats = collect_slice_diff_stats(ws, plan)
            stats_source = stats.source
            diff_unified = stats.unified_diff
            budget = check_slice_diff_budget(stats, block)

            if budget.ok or replan_attempt >= max_replan:
                break

            subdivided = subdivide_slice_plan(
                plan,
                budget=budget,
                config=block,
                stats=stats,
                replan_attempt=replan_attempt + 1,
            )
            if subdivided is None and hermes_use_llm_enabled():
                model = orch._selected_model_for_run(run_id)
                if model:
                    subdivided = execute_slice_replan_llm(
                        rows=orch._store.list_run_events(str(run_id)),
                        base_url=str(runtime.get("base_url", "http://localhost:11434")),
                        model_id=model,
                        prior_plan=plan,
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

            _emit_slice_stage(
                orch,
                run_id,
                "slice.replan",
                metadata={
                    "slice_id": plan.slice_id,
                    "next_slice_id": subdivided.slice_id,
                    "replan_attempt": replan_attempt + 1,
                    "budget_message": budget.message,
                    "diff_stats": {
                        "file_count": len(stats.changed_files),
                        "loc_added": stats.loc_added,
                        "loc_removed": stats.loc_removed,
                        "source": stats.source,
                    },
                },
            )
            plan = subdivided
            budget_feedback = budget.message
            replan_attempt += 1

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
        if hermes_slice_p3_evidence_enabled():
            from hermes_orchestrator.performance_scan import run_ruff_perf
            from hermes_orchestrator.security_scan import run_security_scan

            sec = run_security_scan(ws)
            sec_code = sec[0]
            sec_log = sec[1]
            perf_code, perf_log = run_ruff_perf(ws, timeout_seconds=timeout)
            critique_meta["phase3_evidence"] = {
                "security_scan_exit": sec_code,
                "security_snippet": (sec_log or "")[:1200],
                "performance_scan_exit": perf_code,
                "performance_snippet": (perf_log or "")[:1200],
            }
            if sec_code != 0 or perf_code != 0:
                critique_verdicts = ["FAIL"]
        if hermes_use_llm_enabled():
            model = orch._selected_model_for_run(run_id)
            if model:
                critique_verdicts = execute_slice_critique_llm(
                    plan=plan,
                    base_url=str(runtime.get("base_url", "http://localhost:11434")),
                    model_id=model,
                    verify_log=verify_log,
                    timeout_seconds=timeout,
                )
        critique_meta["critique_verdicts"] = critique_verdicts
        _emit_slice_stage(
            orch,
            run_id,
            "slice.critique",
            metadata=critique_meta,
            duration_ms=0,
        )

        _emit_slice_stage(
            orch,
            run_id,
            "slice.test",
            metadata={"slice_id": plan.slice_id, "tests_passed": tests_passed},
            duration_ms=0,
        )

        e2e_passed: bool | None = None
        e2e_detail = ""
        if block.e2e_enabled:
            from hermes_orchestrator.slice_e2e import run_slice_e2e_verify

            e2e = run_slice_e2e_verify(
                ws,
                command=block.e2e_command,
                timeout_seconds=timeout,
            )
            e2e_passed = e2e.passed
            e2e_detail = e2e.detail
            _emit_slice_stage(
                orch,
                run_id,
                "slice.e2e",
                metadata={
                    "slice_id": plan.slice_id,
                    "e2e_verdict": e2e.verdict,
                    "e2e_exit_code": e2e.exit_code,
                    "e2e_detail": e2e_detail[:2000],
                },
                duration_ms=0,
            )
            if e2e.verdict == "FAIL":
                verify_ok = False
                verify_log = f"{verify_log}\n[e2e] {e2e_detail}"

        final_stats = collect_slice_diff_stats(ws, plan)
        final_budget = check_slice_diff_budget(final_stats, block)
        if not final_budget.ok:
            verify_ok = False
            verify_log = (
                f"{verify_log}\n[diff budget] {final_budget.message} "
                f"(source={stats_source}, replans={replan_attempt})"
            )
        diff_for_gate = diff_unified or final_stats.unified_diff

        gate = orch.record_micro_slice_gate(
            run_id,
            plan,
            verify_ok=verify_ok,
            critique_verdicts=critique_verdicts,
            tests_passed=tests_passed,
            e2e_passed=e2e_passed,
            e2e_detail=e2e_detail,
            diff_unified=diff_for_gate[:8000],
            test_output=test_out[:4000],
        )
        results.append(gate)
        if gate.passed:
            from hermes_orchestrator.slice_git_commit import maybe_commit_slice

            run_meta = orch._run_created_metadata(run_id)
            commit_result = maybe_commit_slice(
                ws,
                plan,
                run_id=str(run_id),
                run_metadata=run_meta,
            )
            if commit_result.get("status") not in ("skipped",):
                _emit_slice_stage(
                    orch,
                    run_id,
                    "slice.git_commit",
                    metadata={"slice_id": plan.slice_id, **commit_result},
                )
        if not gate.passed:
            break
    orch.maybe_rebuild_memory_index(run_id)
    from hermes_orchestrator.git_outputs import emit_git_finalize_after_micro_slice_pass

    emit_git_finalize_after_micro_slice_pass(
        orch,
        run_id,
        ws,
        results,
        emit_stage=_emit_slice_stage,
    )
    return results
