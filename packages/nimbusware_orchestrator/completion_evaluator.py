"""Campaign completion evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    RunCompletedEvent,
    RunCompletedPayload,
    RunFailedEvent,
    RunFailedPayload,
)
from agent_core.models.backlog import SliceStatus
from agent_core.models.events_payloads import (
    CampaignCompletedPayload,
    CampaignFailedPayload,
    CompletionEvaluatedPayload,
)
from agent_core.models.events_records import (
    CampaignCompletedEvent,
    CampaignFailedEvent,
    CompletionEvaluatedEvent,
)
from agent_core.read.campaign import campaign_effective_from_rows
from nimbusware_orchestrator.backlog_generator import apply_slice_outcomes, backlog_from_events
from nimbusware_orchestrator.campaign_slice_selector import all_slices_terminal
from nimbusware_orchestrator.workflow_campaign import CompletionWorkflowBlock

CompletionVerdict = Literal["PASS", "FAIL", "INCOMPLETE"]


@dataclass(frozen=True)
class CompletionEvalResult:
    verdict: CompletionVerdict
    remaining_epics: tuple[str, ...]
    blocking_findings: tuple[str, ...]
    rationale: str
    slices_completed: int = 0
    epics_completed: int = 0


def _completion_policy_from_rows(rows: list[dict[str, Any]]) -> CompletionWorkflowBlock:
    ce = campaign_effective_from_rows(rows)
    if isinstance(ce, dict):
        raw_policy = ce.get("policy")
        if isinstance(raw_policy, dict):
            deep_every = int(raw_policy.get("deep_eval_every_n_slices", 20) or 20)
        else:
            deep_every = 20
        raw_completion = ce.get("completion")
        if isinstance(raw_completion, dict):
            return CompletionWorkflowBlock(
                require_project_tests_pass=bool(
                    raw_completion.get("require_project_tests_pass", True),
                ),
                require_all_must_have_features=bool(
                    raw_completion.get("require_all_must_have_features", True),
                ),
                deep_eval_every_n_slices=max(1, deep_every),
            )
    return CompletionWorkflowBlock()


def _project_tests_passed(rows: list[dict[str, Any]]) -> bool:
    verify_stages = {"slice.verify", "slice.test", "slice.gate", "lifecycle.verify"}
    for row in reversed(rows):
        if row.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        stage = str(payload.get("stage_name") or "")
        verdict = str(payload.get("verdict") or "").upper()
        if stage in verify_stages and verdict == "PASS":
            return True
    return False


def _features_satisfied(backlog: Any) -> bool:
    from agent_core.models.backlog import DeliveryBacklog, SliceStatus

    if not isinstance(backlog, DeliveryBacklog):
        return True
    for epic in backlog.epics:
        for feature in epic.features:
            if not feature.slices:
                return False
            if not any(sl.status == SliceStatus.PASSED for sl in feature.slices):
                return False
    return True


def _deep_eval_due(slices_completed: int, every_n: int) -> bool:
    if slices_completed <= 0:
        return False
    every = max(1, every_n)
    if slices_completed < every:
        return True
    return slices_completed % every == 0


def evaluate_completion(rows: list[dict[str, Any]]) -> CompletionEvalResult:
    """Tiered completion: slice terminal state plus workflow completion policy."""
    policy = _completion_policy_from_rows(rows)
    backlog = backlog_from_events(rows)
    if backlog is None:
        return CompletionEvalResult(
            verdict="INCOMPLETE",
            remaining_epics=(),
            blocking_findings=("no_backlog",),
            rationale="delivery backlog not generated",
        )
    backlog = apply_slice_outcomes(backlog, rows)
    total = backlog.metadata.total_slices_planned
    passed_slices = sum(
        1
        for epic in backlog.epics
        for feature in epic.features
        for sl in feature.slices
        if sl.status == SliceStatus.PASSED
    )
    completed = max(backlog.metadata.slices_completed, passed_slices)
    remaining: list[str] = []
    blocking: list[str] = []
    for epic in backlog.epics:
        pending = any(
            sl.status in (SliceStatus.PENDING, SliceStatus.IN_FLIGHT, SliceStatus.FAILED)
            for feature in epic.features
            for sl in feature.slices
        )
        if pending:
            remaining.append(epic.epic_id)
    if any(
        sl.status == SliceStatus.FAILED
        for epic in backlog.epics
        for feature in epic.features
        for sl in feature.slices
    ):
        blocking.append("failed_slices")

    if all_slices_terminal(backlog) and not blocking and not remaining:
        if policy.require_project_tests_pass and not _project_tests_passed(rows):
            blocking.append("project_tests_not_passed")
        if policy.require_all_must_have_features and not _features_satisfied(backlog):
            blocking.append("must_have_features_incomplete")
        if not _deep_eval_due(completed, policy.deep_eval_every_n_slices):
            blocking.append("deep_eval_cadence_pending")
        from nimbusware_orchestrator.factory_cadence import factory_blocks_campaign_pass

        blocking.extend(factory_blocks_campaign_pass(rows))
        if blocking:
            return CompletionEvalResult(
                verdict="INCOMPLETE",
                remaining_epics=(),
                blocking_findings=tuple(blocking),
                rationale=f"all {total} slices terminal; completion policy not satisfied",
                slices_completed=completed,
                epics_completed=len(backlog.epics),
            )
        return CompletionEvalResult(
            verdict="PASS",
            remaining_epics=(),
            blocking_findings=(),
            rationale=f"all {total} backlog slices passed; completion policy satisfied",
            slices_completed=completed,
            epics_completed=len(backlog.epics),
        )
    return CompletionEvalResult(
        verdict="INCOMPLETE",
        remaining_epics=tuple(remaining),
        blocking_findings=tuple(blocking),
        rationale=f"{completed}/{total} slices complete",
        slices_completed=completed,
    )


def emit_completion_evaluated(
    store: Any,
    run_id: UUID,
    result: CompletionEvalResult,
) -> None:
    store.append(
        CompletionEvaluatedEvent(
            event_type=EventType.COMPLETION_EVALUATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=CompletionEvaluatedPayload(
                verdict=result.verdict,
                remaining_epics=list(result.remaining_epics),
                blocking_findings=list(result.blocking_findings),
                rationale=result.rationale,
            ),
        ),
    )


def emit_campaign_terminal(
    store: Any,
    run_id: UUID,
    result: CompletionEvalResult,
) -> None:
    campaign_id = str(run_id)
    if result.verdict == "PASS":
        store.append(
            CampaignCompletedEvent(
                event_type=EventType.CAMPAIGN_COMPLETED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=CampaignCompletedPayload(
                    campaign_id=campaign_id,
                    slices_completed=result.slices_completed,
                    epics_completed=result.epics_completed,
                    summary=result.rationale,
                ),
            ),
        )
        store.append(
            RunCompletedEvent(
                event_type=EventType.RUN_COMPLETED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=RunCompletedPayload(summary=result.rationale),
            ),
        )
        try:
            from nimbusware_maker.web_push_notify import notify_campaign_completed

            notify_campaign_completed(run_id, summary=result.rationale)
        except Exception:
            pass
        return
    if result.verdict == "FAIL":
        store.append(
            CampaignFailedEvent(
                event_type=EventType.CAMPAIGN_FAILED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=CampaignFailedPayload(
                    campaign_id=campaign_id,
                    reason_code="completion_failed",
                    summary=result.rationale,
                ),
            ),
        )
        store.append(
            RunFailedEvent(
                event_type=EventType.RUN_FAILED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=RunFailedPayload(
                    reason_code="campaign_failed",
                    message=result.rationale,
                ),
            ),
        )
        try:
            from nimbusware_maker.web_push_notify import notify_campaign_failed

            notify_campaign_failed(run_id, summary=result.rationale)
        except Exception:
            pass


def evaluate_and_finalize_campaign(
    store: Any, run_id: UUID, rows: list[dict[str, Any]]
) -> CompletionEvalResult:
    if any(r.get("event_type") == EventType.COMPLETION_EVALUATED.value for r in rows):
        for row in reversed(rows):
            if row.get("event_type") != EventType.COMPLETION_EVALUATED.value:
                continue
            payload = row.get("payload")
            if isinstance(payload, dict):
                raw_verdict = str(payload.get("verdict") or "INCOMPLETE")
                verdict = (
                    cast(CompletionVerdict, raw_verdict)
                    if raw_verdict in ("PASS", "FAIL", "INCOMPLETE")
                    else "INCOMPLETE"
                )
                return CompletionEvalResult(
                    verdict=verdict,
                    remaining_epics=tuple(payload.get("remaining_epics") or []),
                    blocking_findings=tuple(payload.get("blocking_findings") or []),
                    rationale=str(payload.get("rationale") or ""),
                )
    result = evaluate_completion(rows)
    from nimbusware_maker.workspace import resolve_run_workspace
    from nimbusware_orchestrator.factory_cadence import (
        factory_complete_emitted,
        factory_completion_policy_from_rows,
        maybe_run_factory_cadence_pass,
    )

    factory_policy = factory_completion_policy_from_rows(rows)
    if (
        factory_policy is not None
        and result.verdict == "PASS"
        and not factory_complete_emitted(rows)
    ):
        backlog = backlog_from_events(rows)
        completed = backlog.metadata.slices_completed if backlog else 0
        maybe_run_factory_cadence_pass(
            store,
            run_id,
            store.list_run_events(str(run_id)),
            workspace=resolve_run_workspace(rows),
            slices_completed=completed,
            force=True,
        )
        rows = store.list_run_events(str(run_id))
        result = evaluate_completion(rows)
    emit_completion_evaluated(store, run_id, result)
    if result.verdict == "PASS":
        from nimbusware_maker.workspace import resolve_run_workspace
        from nimbusware_orchestrator.launch_evaluator import maybe_run_launch_eval_for_campaign

        maybe_run_launch_eval_for_campaign(
            store,
            run_id,
            store.list_run_events(str(run_id)),
            workspace=resolve_run_workspace(rows),
        )
    if result.verdict in ("PASS", "FAIL"):
        emit_campaign_terminal(store, run_id, result)
    return result
