from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from nimbusware_env.env_flags import nimbusware_slice_p3_evidence_enabled, nimbusware_use_llm_enabled
from nimbusware_orchestrator.micro_slice import SlicePlan
from nimbusware_orchestrator.micro_slice_executor_context import (
    _active_enforcement,
    _emit_slice_stage,
    _launch_test_enabled,
)
from nimbusware_orchestrator.micro_slice_run_context import fast_slice_effective_from_rows
from nimbusware_orchestrator.micro_slice_verify import run_slice_verify_and_test as _run_slice_verify_and_test
from nimbusware_orchestrator.slice_diff import check_slice_diff_budget, collect_slice_diff_stats
from nimbusware_orchestrator.slice_gate import SliceGateChainResult
from nimbusware_orchestrator.slice_implement import slice_implement_mode
from nimbusware_orchestrator.llm_slice import execute_slice_critique_llm

if TYPE_CHECKING:
    from nimbusware_orchestrator.pipeline import RunOrchestrator


def finish_micro_slice_gate_chain(
    orch: RunOrchestrator,
    run_id: UUID,
    *,
    ws: Path,
    rows: list[dict[str, Any]],
    block: Any,
    active_plan: SlicePlan,
    effective_backlog_slice_id: str | None,
    timeout: float,
    runtime: dict[str, Any],
    duration_ms: int,
    diff_unified: str,
    stats_source: str,
    replan_attempt: int,
    profile: Any,
) -> SliceGateChainResult:
    verify_ok, verify_log, tests_passed, test_out = _run_slice_verify_and_test(
        ws,
        active_plan,
        timeout_seconds=timeout,
        rows=rows,
        enforcement_profile=_active_enforcement(rows),
    )
    _emit_slice_stage(
        orch,
        run_id,
        "slice.verify",
        metadata={"slice_id": active_plan.slice_id, "verify_ok": verify_ok},
        duration_ms=duration_ms,
    )

    critique_verdicts = ["PASS"]
    critique_meta: dict[str, Any] = {"slice_id": active_plan.slice_id}
    if effective_backlog_slice_id:
        critique_meta["backlog_slice_id"] = effective_backlog_slice_id
    from nimbusware_orchestrator.enforcement_pipeline import security_scan_required

    enforcement = _active_enforcement(rows)
    if enforcement and security_scan_required(enforcement):
        from nimbusware_orchestrator.verifiers import run_bandit_on_layout
        from nimbusware_orchestrator.workspace_layout import detect_workspace_layout

        layout = detect_workspace_layout(ws)
        b_code, b_out = run_bandit_on_layout(layout, timeout_seconds=timeout)
        critique_meta["enforcement_security"] = {
            "bandit_exit": b_code,
            "snippet": (b_out or "")[:800],
        }
        if b_code != 0:
            critique_verdicts = ["FAIL"]
    elif nimbusware_slice_p3_evidence_enabled():
        from nimbusware_orchestrator.performance_scan import run_ruff_perf
        from nimbusware_orchestrator.security_scan import run_security_scan

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
    rows = orch._store.list_run_events(str(run_id))
    if nimbusware_use_llm_enabled() and not fast_slice_effective_from_rows(rows):
        model = orch._selected_model_for_run(run_id)
        if model:
            critique_verdicts = execute_slice_critique_llm(
                plan=active_plan,
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
        metadata={"slice_id": active_plan.slice_id, "tests_passed": tests_passed},
        duration_ms=0,
    )

    if _launch_test_enabled(rows):
        from nimbusware_orchestrator.dev_env_supervisor import frontend_base_url
        from nimbusware_orchestrator.launch_test_stage import run_launch_test_stage

        preview = frontend_base_url(ws)
        for lt_stage in ("launch_test.plan", "launch_test.write", "launch_test.critique"):
            code, detail, _ = run_launch_test_stage(ws, lt_stage, preview_base_url=preview)
            _emit_slice_stage(
                orch,
                run_id,
                lt_stage,
                metadata={"slice_id": active_plan.slice_id, "detail": detail[:500]},
                duration_ms=0,
            )
            if code != 0:
                verify_ok = False
                verify_log = f"{verify_log}\n[{lt_stage}] {detail}".strip()

    e2e_passed: bool | None = None
    e2e_detail = ""
    if block.e2e_enabled:
        from nimbusware_orchestrator.slice_e2e import run_slice_e2e_verify

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
                "slice_id": active_plan.slice_id,
                "e2e_verdict": e2e.verdict,
                "e2e_exit_code": e2e.exit_code,
                "e2e_detail": e2e_detail[:2000],
            },
            duration_ms=0,
        )
        if e2e.verdict == "FAIL":
            verify_ok = False
            verify_log = f"{verify_log}\n[e2e] {e2e_detail}"

    enforcement = _active_enforcement(rows)
    if enforcement is not None:
        from nimbusware_orchestrator.enforcement_pipeline import normalize_e2e_for_enforcement

        e2e_passed, e2e_detail = normalize_e2e_for_enforcement(
            e2e_passed,
            e2e_detail,
            enforcement,
            e2e_enabled=block.e2e_enabled,
        )

    ensure_dev_environment_for_slice(orch._store, run_id, ws, rows)
    pre_regression = run_pre_gate_dev_env_regression(orch._store, run_id, ws, rows, profile)
    verify_ok, verify_log = merge_pre_gate_into_verify(verify_ok, verify_log, pre_regression)
    fidelity_passed, fidelity_detail = maybe_run_human_fidelity_pre_gate(
        orch._store,
        run_id,
        ws,
        rows,
    )
    if fidelity_passed is False:
        verify_ok = False
        verify_log = f"{verify_log}\n[human_fidelity] {fidelity_detail}".strip()

    final_stats = collect_slice_diff_stats(ws, active_plan)
    if slice_implement_mode() == "stub":
        from nimbusware_orchestrator.slice_diff import SliceDiffStats

        final_stats = SliceDiffStats(
            final_stats.changed_files,
            0,
            0,
            final_stats.unified_diff,
            source="stub_noop",
        )
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
        active_plan,
        verify_ok=verify_ok,
        critique_verdicts=critique_verdicts,
        tests_passed=tests_passed,
        e2e_passed=e2e_passed,
        e2e_detail=e2e_detail,
        diff_unified=diff_for_gate[:8000],
        test_output=test_out[:4000],
    )
    if not gate.passed:
        handle_gate_failure_learning(orch._store, run_id, ws, active_plan, gate)
    gate = apply_operator_pause(
        gate,
        profile,
        dev_env_failed=pre_regression.http_passed is False,
        ui_regression_failed=pre_regression.ui_passed is False,
    )
    if gate.passed:
        from nimbusware_orchestrator.patch_context import (
            patch_auto_apply_allowed,
            patch_effective_from_run_rows,
            work_type_from_run_rows,
        )
        from nimbusware_orchestrator.slice_git_commit import maybe_commit_slice

        patch_eff = patch_effective_from_run_rows(rows)
        wt = work_type_from_run_rows(rows)
        if patch_eff and patch_eff.get("enabled") and (wt == "patch" or patch_eff):
            policy = patch_eff.get("auto_apply_policy") or {}
            if isinstance(policy, dict):
                auto_ok = patch_auto_apply_allowed(
                    policy=policy,
                    files_changed=len(final_stats.changed_files),
                    loc_changed=final_stats.loc_added + final_stats.loc_removed,
                    tests_passed=tests_passed,
                    gate_passed=True,
                )
                if auto_ok:
                    _emit_slice_stage(
                        orch,
                        run_id,
                        "slice.applied",
                        metadata={
                            "slice_id": active_plan.slice_id,
                            "auto_applied": True,
                            "patch_auto_apply": True,
                            **(
                                {"backlog_slice_id": effective_backlog_slice_id}
                                if effective_backlog_slice_id
                                else {}
                            ),
                        },
                    )

        run_meta = orch._run_created_metadata(run_id)
        commit_result = maybe_commit_slice(
            ws,
            active_plan,
            run_id=str(run_id),
            run_metadata=run_meta,
        )
        if commit_result.get("status") not in ("skipped",):
            _emit_slice_stage(
                orch,
                run_id,
                "slice.git_commit",
                metadata={"slice_id": active_plan.slice_id, **commit_result},
            )
    return gate
