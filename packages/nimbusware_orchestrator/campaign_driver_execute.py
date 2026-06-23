from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from agent_core.models import EventType
from agent_core.models.events_payloads import SliceQueuedPayload
from agent_core.models.events_records import SliceQueuedEvent
from nimbusware_orchestrator.backlog_generator import (
    apply_slice_outcomes,
    backlog_from_events,
)
from nimbusware_orchestrator.campaign import CampaignDriverState
from nimbusware_orchestrator.campaign_slice_selector import (
    SelectedSlice,
    all_slices_terminal,
    select_next_slice,
    select_next_slices,
)
from nimbusware_orchestrator.micro_slice import parse_slice_plan

if TYPE_CHECKING:
    from nimbusware_orchestrator.pipeline import RunOrchestrator


@dataclass(frozen=True)
class CampaignTickResult:
    state: CampaignDriverState
    should_continue: bool
    slices_completed: int
    message: str
    last_slice_passed: bool | None = None


def _emit_slice_queued(store: Any, run_id: UUID, *, slice_id: str, epic_id: str) -> None:
    store.append(
        SliceQueuedEvent(
            event_type=EventType.SLICE_QUEUED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=SliceQueuedPayload(
                slice_id=slice_id,
                backlog_slice_id=slice_id,
                epic_id=epic_id,
            ),
        ),
    )


def _parallel_slice_count() -> int:
    from nimbusware_env.settings_resolve import resolve_int

    return max(1, resolve_int("NIMBUSWARE_CAMPAIGN_PARALLEL_SLICES", default=1))


def _select_slices_for_tick(run_id: UUID, backlog: Any) -> list[SelectedSlice]:
    parallel = _parallel_slice_count()
    if parallel <= 1:
        one = select_next_slice(backlog)
        return [one] if one is not None else []
    return select_next_slices(backlog, parallel)


def _execute_campaign_slices(
    orch: RunOrchestrator,
    run_id: UUID,
    *,
    backlog: Any,
    selected_list: list[SelectedSlice],
    workspace: Any | None,
    policy: Any,
) -> CampaignTickResult:
    from nimbusware_compute.mesh_host_sync import (
        absorb_completed_mesh_units,
        campaign_mesh_stage_name,
        campaign_slice_passed_from_mesh,
        wait_for_mesh_units,
    )
    from nimbusware_orchestrator.mesh_pipeline_hook import (
        mesh_assign_campaign_slices,
        resolve_mesh_context_for_run,
    )

    session_id, workload, node_ids = resolve_mesh_context_for_run(run_id)
    assignments: dict[str, UUID | None] = {}
    mesh_active = len(selected_list) > 1 and session_id is not None and node_ids
    if mesh_active:
        assignments = mesh_assign_campaign_slices(
            run_id=run_id,
            slice_ids=[sel.slice.slice_id for sel in selected_list],
            session_id=session_id,
            workload_distribution=workload,
            node_ids=node_ids,
            workspace=workspace,
        )

    remote_by_slice = {
        sel.slice.slice_id: mesh_active and assignments.get(sel.slice.slice_id) is not None
        for sel in selected_list
    }
    remote_stages = [
        campaign_mesh_stage_name(sel.slice.slice_id)
        for sel in selected_list
        if remote_by_slice[sel.slice.slice_id]
    ]

    for selected in selected_list:
        _emit_slice_queued(
            orch._store,
            run_id,
            slice_id=selected.slice.slice_id,
            epic_id=selected.epic_id,
        )

    last_passed: bool | None = None
    completed = backlog.metadata.slices_completed

    def _handle_slice_failure(*, passed: bool) -> CampaignTickResult | None:
        nonlocal last_passed, completed
        last_passed = passed
        if passed:
            return None
        rows = orch._store.list_run_events(str(run_id))
        failures = _consecutive_slice_failures(rows)
        max_fail = policy.max_consecutive_slice_failures if policy else 5
        if failures >= max_fail:
            return CampaignTickResult(
                state=CampaignDriverState.FAILED,
                should_continue=False,
                slices_completed=completed,
                message=f"slice failed; {failures} consecutive failures",
                last_slice_passed=False,
            )
        return CampaignTickResult(
            state=CampaignDriverState.EXECUTING,
            should_continue=True,
            slices_completed=completed,
            message="slice failed; will retry next eligible slice",
            last_slice_passed=False,
        )

    for selected in selected_list:
        if remote_by_slice[selected.slice.slice_id]:
            continue
        rows = orch._store.list_run_events(str(run_id))
        backlog = apply_slice_outcomes(backlog_from_events(rows) or backlog, rows)
        completed = backlog.metadata.slices_completed
        plan = parse_slice_plan(
            {
                "slice_id": selected.slice.slice_id,
                "rationale": selected.slice.rationale,
                "target_paths": list(selected.slice.target_paths),
                "acceptance_criteria": "Campaign backlog slice",
            },
        )
        gate = orch.execute_single_micro_slice(
            run_id,
            slice_index=completed + 1,
            workspace=workspace,
            plan=plan,
            backlog_slice_id=selected.slice.slice_id,
        )
        rows = orch._store.list_run_events(str(run_id))
        backlog = apply_slice_outcomes(backlog_from_events(rows) or backlog, rows)
        completed = backlog.metadata.slices_completed
        failure = _handle_slice_failure(passed=gate.passed)
        if failure is not None:
            return failure

    if remote_stages:
        ws_path = Path(workspace).resolve() if workspace is not None else None
        wait_for_mesh_units(run_id, remote_stages)
        absorb_completed_mesh_units(
            orch._store,
            run_id,
            remote_stages,
            host_workspace=ws_path,
        )
        rows = orch._store.list_run_events(str(run_id))
        backlog = apply_slice_outcomes(backlog_from_events(rows) or backlog, rows)
        completed = backlog.metadata.slices_completed
        for selected in selected_list:
            if not remote_by_slice[selected.slice.slice_id]:
                continue
            passed = campaign_slice_passed_from_mesh(run_id, selected.slice.slice_id)
            failure = _handle_slice_failure(passed=passed)
            if failure is not None:
                return failure

    rows = orch._store.list_run_events(str(run_id))
    if all_slices_terminal(apply_slice_outcomes(backlog, rows)):
        from nimbusware_orchestrator.completion_evaluator import evaluate_and_finalize_campaign

        eval_result = evaluate_and_finalize_campaign(orch._store, run_id, rows)
        state = (
            CampaignDriverState.COMPLETED
            if eval_result.verdict == "PASS"
            else CampaignDriverState.ASSESSING
        )
        return CampaignTickResult(
            state=state,
            should_continue=False,
            slices_completed=completed,
            message=eval_result.rationale,
            last_slice_passed=last_passed,
        )

    return CampaignTickResult(
        state=CampaignDriverState.EXECUTING,
        should_continue=True,
        slices_completed=completed,
        message="slice passed; more work remains",
        last_slice_passed=last_passed,
    )


def _count_passed_slices(rows: list[dict[str, Any]]) -> int:
    backlog = backlog_from_events(rows)
    if backlog is None:
        return 0
    return apply_slice_outcomes(backlog, rows).metadata.slices_completed


def _consecutive_slice_failures(rows: list[dict[str, Any]]) -> int:
    streak = 0
    for row in reversed(rows):
        payload = row.get("payload")
        if not isinstance(payload, dict) or payload.get("stage_name") != "slice.gate":
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        if meta.get("slice_gate_verdict") == "PASS":
            break
        streak += 1
    return streak
