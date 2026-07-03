from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from agent_core.models import EventType
from agent_core.models.events_payloads import CampaignPausedPayload, SliceQueuedPayload
from agent_core.models.events_records import CampaignPausedEvent, SliceQueuedEvent
from env import find_repo_root
from orchestrator.campaign.generator import (
    emit_backlog_generated,
    generate_heuristic_backlog,
)
from orchestrator.pipeline import make_dev_orchestrator
from projections.builders.campaign_progress import campaign_progress_from_events


def test_campaign_progress_none_for_non_campaign_run() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("default")
    rows = store.list_run_events(str(run_id))
    assert campaign_progress_from_events(rows) is None


def test_campaign_progress_executing_with_slice_and_maintenance_schedule() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run(
        "campaign_micro_slice",
        requirements={"business_prompt": "Build auth"},
        autonomous=True,
    )
    backlog = generate_heuristic_backlog(str(run_id), max_slices=5)
    emit_backlog_generated(store, run_id, backlog)
    first_slice = backlog.epics[0].features[0].slices[0]
    store.append(
        SliceQueuedEvent(
            event_type=EventType.SLICE_QUEUED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=SliceQueuedPayload(
                slice_id=first_slice.slice_id,
                backlog_slice_id=first_slice.slice_id,
                epic_id=backlog.epics[0].epic_id,
            ),
        ),
    )
    rows = store.list_run_events(str(run_id))
    progress = campaign_progress_from_events(rows)
    assert progress is not None
    assert progress["state"] == "executing"
    assert progress["autonomous"] is True
    assert progress["current_slice_id"] == first_slice.slice_id
    assert progress["slices_total"] == backlog.metadata.total_slices_planned
    assert progress["next_maintenance"]["refactor_in_slices"] == 5
    assert progress["next_maintenance"]["architecture_in_slices"] == 10


def test_campaign_progress_paused_state() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("campaign_micro_slice", autonomous=True)
    store.append(
        CampaignPausedEvent(
            event_type=EventType.CAMPAIGN_PAUSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=CampaignPausedPayload(
                campaign_id=str(run_id),
                reason_code="operator_pause",
                operator_initiated=True,
            ),
        ),
    )
    rows = store.list_run_events(str(run_id))
    progress = campaign_progress_from_events(rows)
    assert progress is not None
    assert progress["state"] == "paused"
