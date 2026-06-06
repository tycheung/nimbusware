from __future__ import annotations

from pathlib import Path

from agent_core.models import EventType
from agent_core.models.backlog import (
    BacklogEpic,
    BacklogFeature,
    BacklogSlice,
    DeliveryBacklog,
    SliceStatus,
)
from nimbusware_env import find_repo_root
from nimbusware_orchestrator.backlog_generator import emit_backlog_generated
from nimbusware_orchestrator.completion_evaluator import (
    evaluate_and_finalize_campaign,
    evaluate_completion,
)
from nimbusware_orchestrator.pipeline import make_dev_orchestrator


def test_evaluate_completion_incomplete_without_backlog() -> None:
    result = evaluate_completion([])
    assert result.verdict == "INCOMPLETE"


def test_evaluate_completion_pass_when_all_slices_passed() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("campaign_micro_slice")
    backlog = DeliveryBacklog(
        campaign_id=str(run_id),
        epics=(
            BacklogEpic(
                epic_id="e1",
                title="E",
                features=(
                    BacklogFeature(
                        feature_id="f1",
                        title="F",
                        slices=(
                            BacklogSlice(slice_id="s1", status=SliceStatus.PASSED),
                        ),
                    ),
                ),
            ),
        ),
    )
    emit_backlog_generated(store, run_id, backlog)
    rows = store.list_run_events(str(run_id))
    result = evaluate_and_finalize_campaign(store, run_id, rows)
    assert result.verdict == "PASS"
    types = [r.get("event_type") for r in store.list_run_events(str(run_id))]
    assert EventType.CAMPAIGN_COMPLETED.value in types
    assert EventType.RUN_COMPLETED.value in types
