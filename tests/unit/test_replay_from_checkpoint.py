from __future__ import annotations

from uuid import uuid4

import pytest

from orchestrator.context_compaction import maybe_emit_compaction_event
from orchestrator.replay.replay_from import (
    ReplayPolicy,
    compaction_allowed,
    emit_replay_started_event,
)
from store.memory import InMemoryEventStore


def _handoff_event(seq: int, summary: str) -> dict:
    return {
        "seq": seq,
        "store_seq": seq,
        "payload": {"stage_name": "slice.handoff"},
        "metadata": {"handoff_summary": summary, "slice_id": f"s{seq}"},
    }


def test_replay_policy_disables_compaction() -> None:
    store = InMemoryEventStore()
    run_id = uuid4()
    events = [_handoff_event(i, "x" * 500) for i in range(1, 6)]
    emit_replay_started_event(
        store,
        run_id=run_id,
        from_store_seq=3,
        replay_policy=ReplayPolicy(compact_enabled=False),
        operator_ack=True,
    )
    rows = store.list_run_events(str(run_id)) + events
    assert compaction_allowed(rows) is False
    result = maybe_emit_compaction_event(
        store,
        run_id=run_id,
        events=rows,
        keep_recent_tokens=150,
        reserve_tokens=50,
    )
    assert result is None


def test_replay_from_api_route() -> None:
    from fastapi.testclient import TestClient

    from api.app import app

    with TestClient(app) as tc:
        create = tc.post("/v1/runs", json={"workflow_profile": "default"})
        assert create.status_code in (200, 201)
        run_id = create.json()["run_id"]
        denied = tc.post(
            f"/v1/runs/{run_id}/replay-from",
            json={"from_store_seq": 1, "operator_ack": False},
        )
        assert denied.status_code == 422
        ok = tc.post(
            f"/v1/runs/{run_id}/replay-from",
            json={"from_store_seq": 1, "operator_ack": True, "compact_enabled": False},
        )
        assert ok.status_code == 200
        body = ok.json()
        assert body["replay_started"] is True
        assert body["compact_enabled"] is False


def test_replay_from_enqueues_campaign_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path

    from fastapi.testclient import TestClient

    from api.app import app
    from orchestrator.run_dispatch import InMemoryRunQueue, get_run_queue, set_run_queue

    monkeypatch.setenv("NIMBUSWARE_RUN_DISPATCH", "memory")
    queue = InMemoryRunQueue()
    set_run_queue(queue)
    repo = Path(__file__).resolve().parents[2]
    ws = str((repo / "tests" / "fixtures" / "repos" / "tiny_python_app").resolve()).replace(
        "\\", "/"
    )
    with TestClient(app) as tc:
        tc.app.state.run_queue = queue
        project = tc.post(
            "/v1/projects",
            json={"name": "replay-campaign", "workspace_path": ws, "template": "attach"},
            headers={
                "X-Nimbusware-Admin-Token": "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"
            },
        )
        assert project.status_code == 200
        pid = project.json()["project_id"]
        campaign = tc.post(
            "/v1/campaigns",
            json={
                "project_id": pid,
                "requirements": {"business_prompt": "replay tick enqueue"},
                "autonomous": False,
                "workflow_profile": "campaign_micro_slice",
            },
            headers={
                "X-Nimbusware-Admin-Token": "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"
            },
        )
        assert campaign.status_code == 200
        run_id = campaign.json()["run_id"]
        while get_run_queue().stats()["pending"]:
            task = get_run_queue().dequeue()
            if task is not None:
                tc.app.state.orchestrator.process_campaign_dispatch_task(task)
                get_run_queue().ack(task.task_id)
        replay = tc.post(
            f"/v1/runs/{run_id}/replay-from",
            json={"from_store_seq": 1, "operator_ack": True},
        )
        assert replay.status_code == 200
        body = replay.json()
        assert body["campaign_tick_enqueued"] is True
        assert get_run_queue().stats()["pending"] >= 1
