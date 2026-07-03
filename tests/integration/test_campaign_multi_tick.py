from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from agent_core.models import EventType
from agent_core.models.events_payloads import StagePassedPayload
from agent_core.models.events_records import StagePassedEvent
from e2e.harness.timeline import assert_timeline_golden
from env import find_repo_root
from orchestrator.campaign.campaign import CampaignDriverState
from orchestrator.campaign.driver import campaign_driver_tick
from orchestrator.campaign.generator import generate_heuristic_backlog
from orchestrator.pipeline import make_dev_orchestrator
from orchestrator.slice.gate import SliceGateChainResult
from orchestrator.workflow.campaign import CompletionWorkflowBlock

CAMPAIGN_GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "campaign"
    / "golden_multi_tick_timeline.json"
)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _dispatch_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_RUN_DISPATCH", "memory")
    monkeypatch.setenv("NIMBUSWARE_MICRO_SLICE_COUNT", "1")


def _relaxed_policy(rows: list) -> CompletionWorkflowBlock:
    del rows
    return CompletionWorkflowBlock(
        require_project_tests_pass=False,
        require_all_must_have_features=False,
        deep_eval_every_n_slices=1,
    )


def _emit_slice_gate_pass(store: object, run_id: UUID, *, backlog_slice_id: str) -> None:
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "backlog_slice_id": backlog_slice_id,
                "slice_id": backlog_slice_id,
                "slice_gate_verdict": "PASS",
            },
            payload=StagePassedPayload(stage_name="slice.gate", duration_ms=0),
        ),
    )


def test_campaign_multi_tick_reaches_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    monkeypatch.setattr(
        "orchestrator.completion_evaluator._completion_policy_from_rows",
        _relaxed_policy,
    )

    def _two_slice_backlog(campaign_id: str, **kwargs: object):
        return generate_heuristic_backlog(campaign_id, max_slices=2)

    monkeypatch.setattr(
        "orchestrator.campaign.generator.generate_heuristic_backlog",
        _two_slice_backlog,
    )

    def _fast_slice(
        orchestrator_host: object,
        run_id: UUID,
        *,
        slice_index: int,
        workspace: object = None,
        plan: object = None,
        backlog_slice_id: str | None = None,
    ) -> SliceGateChainResult:
        del slice_index, workspace, plan
        sid = backlog_slice_id or "slice-001"
        from orchestrator.pipeline import RunOrchestrator

        assert isinstance(orchestrator_host, RunOrchestrator)
        _emit_slice_gate_pass(orchestrator_host._store, run_id, backlog_slice_id=sid)
        return SliceGateChainResult(slice_id=sid, passed=True, steps=(), status="passed")

    monkeypatch.setattr(
        "orchestrator.slice.executor.execute_single_micro_slice",
        _fast_slice,
    )

    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run(
        "campaign_micro_slice",
        requirements={"business_prompt": "two slice campaign"},
        autonomous=True,
    )
    orch.start_campaign(run_id, workspace=repo)

    for _ in range(12):
        result = campaign_driver_tick(orch, run_id, workspace=repo)
        if result.state == CampaignDriverState.COMPLETED:
            break

    rows = store.list_run_events(str(run_id))
    types = {r.get("event_type") for r in rows}
    assert EventType.CAMPAIGN_CREATED.value in types
    assert EventType.DELIVERY_BACKLOG_GENERATED.value in types
    assert EventType.CAMPAIGN_COMPLETED.value in types

    golden = json.loads(CAMPAIGN_GOLDEN.read_text(encoding="utf-8"))
    assert_timeline_golden(rows, golden)
    assert result.state == CampaignDriverState.COMPLETED
