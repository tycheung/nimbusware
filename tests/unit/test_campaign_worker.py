from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_orchestrator.run_dispatch import InMemoryRunQueue, set_run_queue
from nimbusware_orchestrator.run_worker import run_worker_loop


@pytest.fixture(autouse=True)
def _dispatch_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_RUN_DISPATCH", "memory")
    monkeypatch.setenv("NIMBUSWARE_MICRO_SLICE_COUNT", "1")


def test_run_worker_processes_campaign_tick() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    queue = InMemoryRunQueue()
    set_run_queue(queue)
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("campaign_micro_slice")
    orch.start_campaign(run_id, workspace=repo)
    assert queue.stats()["pending"] >= 1
    processed = run_worker_loop(queue, orch, max_tasks=1, max_idle_loops=5)
    assert processed == 1
    rows = store.list_run_events(str(run_id))
    assert "campaign.tick" in [
        (r.get("payload") or {}).get("stage_name")
        for r in rows
        if isinstance(r.get("payload"), dict)
    ]
