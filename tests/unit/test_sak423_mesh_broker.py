from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest

from broker_client.stage_bind.compute import (
    build_compute_list_payload,
    build_compute_register_payload,
)
from compute.mesh_host_sync import wait_for_mesh_units, writer_stage_result_from_mesh
from compute.work_unit import WorkUnitRecord
from compute.work_unit_execute import execute_work_unit_on_worker


def test_build_compute_list_payload() -> None:
    out = build_compute_list_payload(
        run_id="r1",
        stage_name="implementation",
        status="completed",
        limit=10,
    )
    assert out == {
        "action": "list",
        "run_id": "r1",
        "stage_name": "implementation",
        "status": "completed",
        "limit": 10,
    }


def test_register_payload_includes_session() -> None:
    out = build_compute_register_payload("w", caps=["mesh_worker"], session_id="s1")
    assert out["session_id"] == "s1"
    assert out["action"] == "register"


def test_wait_for_mesh_units_broker_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    assert wait_for_mesh_units(uuid4(), []) is True


def test_wait_for_mesh_units_broker_poll(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    run_id = uuid4()
    calls = {"n": 0}

    def _via(payload: dict, **_kwargs: object) -> dict:
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "work": [
                    {
                        "kind": "implementation",
                        "status": "claimed",
                        "payload": {"run_id": str(run_id), "stage_name": "implementation"},
                    }
                ]
            }
        return {
            "work": [
                {
                    "kind": "implementation",
                    "status": "completed",
                    "payload": {"run_id": str(run_id), "stage_name": "implementation"},
                    "result": {"verifier_exit_code": 0},
                }
            ]
        }

    with (
        patch(
            "broker_client.stage_bind.compute.compute_work_via_broker",
            side_effect=_via,
        ),
        patch("compute.mesh_host_sync.mesh_poll_interval_seconds", return_value=0.01),
        patch("compute.mesh_host_sync.mesh_wait_timeout_seconds", return_value=2.0),
    ):
        assert wait_for_mesh_units(run_id, ["implementation"]) is True
    assert calls["n"] >= 2


def test_writer_stage_result_from_mesh_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    run_id = uuid4()
    with patch(
        "broker_client.stage_bind.compute.compute_work_via_broker",
        return_value={
            "work": [
                {
                    "kind": "implementation",
                    "status": "completed",
                    "payload": {"run_id": str(run_id), "stage_name": "implementation"},
                    "result": {"verifier_exit_code": 0, "verifier_log": "ok"},
                }
            ]
        },
    ):
        out = writer_stage_result_from_mesh(run_id, "implementation")
    assert out.verifier_exit_code == 0


def test_work_unit_execute_refuses_under_compute_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    rec = WorkUnitRecord(
        work_unit_id=uuid4(),
        run_id=uuid4(),
        session_id=None,
        stage_name="implementation",
        agent_role="implementation",
        executor_user_id="",
        status="assigned",
        payload={},
    )
    with pytest.raises(RuntimeError, match=r"COMPUTE=1\|2"):
        execute_work_unit_on_worker(rec)


def test_api_compute_refuse_under_compute_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    from fastapi import HTTPException

    from broker_client.flags import broker_compute_only

    def refuse() -> None:
        if broker_compute_only():
            raise HTTPException(status_code=503, detail="broker_compute_only")

    with pytest.raises(HTTPException) as exc_info:
        refuse()
    assert exc_info.value.status_code == 503


def test_fleet_mesh_broker_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    from broker_client.stage_bind.compute import node_id_from_broker_record

    nodes_raw = {
        "nodes": [{"id": "11111111-2222-3333-4444-555555555555", "label": "w", "caps": []}]
    }
    work_raw = {"work": [{"status": "queued"}]}
    nodes = []
    for item in nodes_raw["nodes"]:
        nodes.append({"node_id": node_id_from_broker_record(item), "via": "broker"})
    out = {
        "via": "broker",
        "nodes": nodes,
        "queue_depth": len(work_raw["work"]),
    }
    assert out["via"] == "broker"
    assert out["queue_depth"] == 1
    assert out["nodes"][0]["node_id"].startswith("11111111")
