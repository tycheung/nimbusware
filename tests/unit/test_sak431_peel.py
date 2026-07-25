from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from broker_client.client import BrokerClient
from broker_client.stage_bind.compute import build_compute_enqueue_payload
from compute.broker_miss import broker_miss
from compute.broker_route import miss, refuse_broker_only_http


def test_broker_route_miss_shape() -> None:
    out = miss("x", work_unit=None)
    assert out["via"] == "broker_miss"
    assert out["error"] == "x"
    assert out["work_unit"] is None


def test_refuse_broker_only_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as ei:
        refuse_broker_only_http()
    assert ei.value.status_code == 503


def test_broker_client_enqueue_work() -> None:
    calls: list[dict] = []

    class _Fake(BrokerClient):
        def compute_work(self, payload: dict) -> dict:  # type: ignore[override]
            calls.append(payload)
            return {"work": {"id": "w1", "status": "queued"}, "action": "enqueue"}

    client = _Fake.__new__(_Fake)
    out = BrokerClient.enqueue_work(client, "echo", {"n": 1})
    assert out["action"] == "enqueue"
    assert calls[0] == build_compute_enqueue_payload("echo", {"n": 1})


def test_enqueue_payload_known() -> None:
    p = build_compute_enqueue_payload("mesh_stage", {"run_id": "r1", "session_id": "s1"})
    assert p["action"] == "enqueue"
    assert p["kind"] == "mesh_stage"
    assert p["payload"]["session_id"] == "s1"


def test_claim_miss_shape_matches_route() -> None:
    """sak431-b: COMPUTE=1 claim miss returns broker_miss (no local queue)."""
    out = miss("broker down", work_unit=None)
    assert out == {
        "via": "broker_miss",
        "error": "broker down",
        "node": None,
        "work_unit": None,
    }


def test_session_compute_status_miss_shape() -> None:
    out = broker_miss(
        error="x",
        extra={"session_id": str(uuid4()), "nodes": [], "queue_depth": 0},
    )
    assert out["via"] == "broker_miss"
    assert out["queue_depth"] == 0


def test_pipeline_refuse_compute_1(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from orchestrator.collab.pipeline_hook import mesh_assign_parallel_stages

    with (
        patch(
            "orchestrator.compute_broker_bridge.try_broker_compute_work",
            return_value=None,
        ),
        patch("env.find_repo_root", return_value=str(tmp_path)),
        patch(
            "maker.user_agent_overlay.prompt_extension_for_taxonomy_key",
            return_value="",
        ),
        patch(
            "orchestrator.collab.mesh_bindings.executor_binding_hint",
            return_value=None,
        ),
        patch("orchestrator.collab.pipeline_hook.get_mesh_scheduler") as sched_mod,
    ):
        sched = MagicMock()
        nid = uuid4()
        sched.assign.return_value = {"implementation": nid}
        sched_mod.return_value = sched
        with pytest.raises(RuntimeError, match="queue.enqueue"):
            mesh_assign_parallel_stages(
                run_id=uuid4(),
                stage_names=["implementation"],
                session_id=uuid4(),
                workload_distribution="mesh",
                node_ids=[nid],
                workspace=tmp_path,
            )


def test_worker_execute_miss_under_compute_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from compute.work_unit import WorkUnitRecord
    from compute.worker_cli import execute_claimed_work_unit

    rec = WorkUnitRecord(
        work_unit_id=uuid4(),
        run_id=uuid4(),
        session_id=None,
        stage_name="implementation",
        agent_role="implementation",
        executor_user_id="",
        status="assigned",
        payload={"mesh_assignment": True},
    )
    with (
        patch(
            "orchestrator.compute_broker_bridge.try_broker_compute_work",
            return_value=None,
        ),
        patch(
            "compute.worker_cli.execute_work_unit_on_worker",
            side_effect=AssertionError("no local"),
        ),
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            execute_claimed_work_unit(rec)
