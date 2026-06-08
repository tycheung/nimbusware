"""Campaign driver state machine — one slice per tick."""

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
    effective_backlog_generator_mode,
    ensure_backlog,
)
from nimbusware_orchestrator.campaign import (
    CampaignDriverState,
    campaign_effective_from_rows,
    campaign_enabled_for_run,
    campaign_policy_from_rows,
)
from nimbusware_orchestrator.campaign_slice_selector import all_slices_terminal, select_next_slice
from nimbusware_orchestrator.context_compaction import maybe_emit_compaction_event
from nimbusware_orchestrator.micro_slice import parse_slice_plan
from nimbusware_projections.builders.context_budget import estimate_context_budget

if TYPE_CHECKING:
    from nimbusware_orchestrator.pipeline import RunOrchestrator


@dataclass(frozen=True)
class CampaignTickResult:
    state: CampaignDriverState
    should_continue: bool
    slices_completed: int
    message: str
    last_slice_passed: bool | None = None


def _terminal_campaign_state(rows: list[dict[str, Any]]) -> CampaignDriverState | None:
    for row in reversed(rows):
        et = row.get("event_type")
        if et == EventType.CAMPAIGN_COMPLETED.value:
            return CampaignDriverState.COMPLETED
        if et == EventType.CAMPAIGN_FAILED.value:
            return CampaignDriverState.FAILED
        if et == EventType.CAMPAIGN_PAUSED.value:
            return CampaignDriverState.PAUSED
    return None


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


def _emit_campaign_tick_marker(store: Any, run_id: UUID, *, tick_seq: int, note: str) -> None:
    from agent_core.models import (
        StagePassedEvent,
        StagePassedPayload,
        StageStartedEvent,
        StageStartedPayload,
    )

    now = datetime.now(timezone.utc)
    meta = {"campaign_tick_seq": tick_seq, "note": note}
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=now,
            metadata=meta,
            payload=StageStartedPayload(stage_name="campaign.tick", attempt=1),
        ),
    )
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata=meta,
            payload=StagePassedPayload(stage_name="campaign.tick", duration_ms=0),
        ),
    )


def _latest_tick_seq(rows: list[dict[str, Any]]) -> int:
    latest = 0
    for row in rows:
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        if payload.get("stage_name") != "campaign.tick":
            continue
        meta = row.get("metadata")
        if isinstance(meta, dict):
            seq = meta.get("campaign_tick_seq")
            if isinstance(seq, int) and seq > latest:
                latest = seq
    return latest


def campaign_driver_tick(
    orch: RunOrchestrator,
    run_id: UUID,
    *,
    workspace: Any | None = None,
) -> CampaignTickResult:
    """Execute one campaign driver tick (plan → single slice → assess)."""
    rows = orch._store.list_run_events(str(run_id))
    if not campaign_enabled_for_run(rows):
        return CampaignTickResult(
            state=CampaignDriverState.FAILED,
            should_continue=False,
            slices_completed=0,
            message="campaign not enabled for run",
        )

    terminal = _terminal_campaign_state(rows)
    if terminal is not None:
        return CampaignTickResult(
            state=terminal,
            should_continue=False,
            slices_completed=_count_passed_slices(rows),
            message=f"campaign in terminal state: {terminal.value}",
        )

    policy = campaign_policy_from_rows(rows)
    ce = campaign_effective_from_rows(rows) or {}
    max_slices = int((ce.get("policy") or {}).get("max_slices", 500) if ce else 500)
    generator_mode, _ = effective_backlog_generator_mode(
        str((ce.get("policy") or {}).get("backlog_generator", "stub")),
    )

    from nimbusware_orchestrator.campaign_safety import (
        campaign_exceeded_duration,
        should_defer_tick_for_pressure,
    )

    if policy and campaign_exceeded_duration(rows, max_hours=policy.max_campaign_duration_hours):
        return CampaignTickResult(
            state=CampaignDriverState.FAILED,
            should_continue=False,
            slices_completed=_count_passed_slices(rows),
            message="campaign exceeded max duration",
        )
    if should_defer_tick_for_pressure(rows):
        return CampaignTickResult(
            state=CampaignDriverState.PAUSED,
            should_continue=True,
            slices_completed=_count_passed_slices(rows),
            message="deferred tick due to resource pressure",
        )

    maybe_emit_compaction_event(
        orch._store,
        run_id=run_id,
        events=rows,
        compaction_trigger="auto_tick",
    )
    rows = orch._store.list_run_events(str(run_id))
    budget = estimate_context_budget(rows)
    tick_seq = _latest_tick_seq(rows) + 1
    put_note = ""
    if workspace is not None:
        try:
            from nimbusware_orchestrator.put_runtime import put_stack_note

            ws_path = Path(workspace)
            put_note = put_stack_note(ws_path)
        except (TypeError, ValueError, OSError):
            put_note = ""
    _emit_campaign_tick_marker(
        orch._store,
        run_id,
        tick_seq=tick_seq,
        note=f"context_advisory={budget.get('advisory_level', 'green')}{put_note}",
    )

    backlog = ensure_backlog(
        orch._store,
        run_id,
        rows,
        generator_mode=generator_mode,
        max_slices=max_slices,
        repo_root=orch.repo_root,
    )
    rows = orch._store.list_run_events(str(run_id))
    backlog = apply_slice_outcomes(backlog, rows)
    completed = backlog.metadata.slices_completed
    policy = campaign_policy_from_rows(rows)
    if policy:
        from nimbusware_orchestrator.maintenance_architecture import (
            run_maintenance_architecture,
            should_run_architecture_pass,
        )
        from nimbusware_orchestrator.maintenance_refactor import (
            run_maintenance_refactor,
            should_run_refactor_pass,
        )

        ce_meta = campaign_effective_from_rows(rows) or {}
        raw_maint = ce_meta.get("maintenance")
        maint: dict[str, Any] = raw_maint if isinstance(raw_maint, dict) else {}
        if should_run_refactor_pass(completed, policy.refactor_every_n_slices):
            run_maintenance_refactor(
                orch,
                run_id,
                slices_completed=completed,
                insert_fix_slices=bool(maint.get("refactor_inserts_fix_slices", True)),
            )
            rows = orch._store.list_run_events(str(run_id))
            backlog = apply_slice_outcomes(backlog_from_events(rows) or backlog, rows)
        if should_run_architecture_pass(completed, policy.architecture_every_n_slices):
            run_maintenance_architecture(
                orch,
                run_id,
                slices_completed=completed,
                can_revise_backlog=bool(maint.get("architecture_can_revise_backlog", True)),
            )
            rows = orch._store.list_run_events(str(run_id))
            backlog = apply_slice_outcomes(backlog_from_events(rows) or backlog, rows)

    if all_slices_terminal(backlog):
        from nimbusware_orchestrator.completion_evaluator import evaluate_and_finalize_campaign

        eval_result = evaluate_and_finalize_campaign(orch._store, run_id, rows)
        if eval_result.verdict == "PASS":
            return CampaignTickResult(
                state=CampaignDriverState.COMPLETED,
                should_continue=False,
                slices_completed=eval_result.slices_completed,
                message=eval_result.rationale,
            )
        return CampaignTickResult(
            state=CampaignDriverState.ASSESSING,
            should_continue=False,
            slices_completed=backlog.metadata.slices_completed,
            message=eval_result.rationale,
        )

    selected = select_next_slice(backlog)
    if selected is None:
        return CampaignTickResult(
            state=CampaignDriverState.ASSESSING,
            should_continue=False,
            slices_completed=backlog.metadata.slices_completed,
            message="no eligible pending slice",
        )

    _emit_slice_queued(
        orch._store,
        run_id,
        slice_id=selected.slice.slice_id,
        epic_id=selected.epic_id,
    )
    plan = parse_slice_plan(
        {
            "slice_id": selected.slice.slice_id,
            "rationale": selected.slice.rationale,
            "target_paths": list(selected.slice.target_paths),
            "acceptance_criteria": "Campaign backlog slice",
        },
    )
    slice_index = backlog.metadata.slices_completed + 1
    gate = orch.execute_single_micro_slice(
        run_id,
        slice_index=slice_index,
        workspace=workspace,
        plan=plan,
        backlog_slice_id=selected.slice.slice_id,
    )

    rows = orch._store.list_run_events(str(run_id))
    backlog = apply_slice_outcomes(backlog_from_events(rows) or backlog, rows)
    completed = backlog.metadata.slices_completed

    if not gate.passed:
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
            last_slice_passed=True,
        )

    return CampaignTickResult(
        state=CampaignDriverState.EXECUTING,
        should_continue=True,
        slices_completed=completed,
        message="slice passed; more work remains",
        last_slice_passed=True,
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
