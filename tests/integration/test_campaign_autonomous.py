from __future__ import annotations

from pathlib import Path

import pytest

from agent_core.models import EventType
from nimbusware_env import find_repo_root
from nimbusware_orchestrator.pipeline import make_dev_orchestrator


@pytest.fixture(autouse=True)
def _stub_slices(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_MICRO_SLICE_COUNT", "1")


def test_campaign_driver_stub_backlog_generates_events() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run(
        "campaign_micro_slice",
        requirements={"business_prompt": "hello campaign"},
        autonomous=True,
    )
    orch.start_campaign(run_id, workspace=repo)
    rows = store.list_run_events(str(run_id))
    types = {r.get("event_type") for r in rows}
    assert EventType.CAMPAIGN_CREATED.value in types
    assert (
        EventType.DELIVERY_BACKLOG_GENERATED.value in types or EventType.SLICE_QUEUED.value in types
    )
