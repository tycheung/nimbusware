from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest

from broker_client.client import BrokerClient
from broker_client.stage_bind.compute import (
    build_compute_claim_payload,
    build_compute_complete_payload,
    build_compute_get_payload,
)
from compute.broker_route import map_broker_compute_http_error, miss
from compute.mesh_stage_runner import execute_mesh_stage_on_worker
from compute.work_unit import WorkUnitRecord
from compute.work_unit_execute import execute_work_unit_on_worker


def _rec() -> WorkUnitRecord:
    return WorkUnitRecord(
        work_unit_id=uuid4(),
        run_id=uuid4(),
        session_id=None,
        stage_name="implementation",
        agent_role="implementation",
        executor_user_id="",
        status="assigned",
        payload={"mesh_assignment": True},
    )


def test_mesh_stage_runner_refuses_compute_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with pytest.raises(RuntimeError, match="COMPUTE=1"):
        execute_mesh_stage_on_worker(_rec())


def test_work_unit_execute_refuses_compute_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with pytest.raises(RuntimeError, match="COMPUTE=1"):
        execute_work_unit_on_worker(_rec())


def test_mesh_event_replay_refuses_compute_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from compute.mesh_event_replay import baseline_event_ids

    with pytest.raises(RuntimeError, match="COMPUTE=1"):
        baseline_event_ids(None, uuid4())  # type: ignore[arg-type]


def test_map_broker_compute_http_error_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak444-c: claim soft path removed; miss mapper remains the contract."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    out = map_broker_compute_http_error(
        RuntimeError("down"),
        feature="compute_claim",
        miss_extra={"work_unit": None},
    )
    assert out["via"] == "broker_miss"
    assert out["work_unit"] is None
    assert miss("x", work_unit=None)["via"] == "broker_miss"


def test_broker_client_claim_complete_get() -> None:
    calls: list[dict] = []

    class _Fake(BrokerClient):
        def compute_work(self, payload: dict) -> dict:  # type: ignore[override]
            calls.append(payload)
            action = payload["action"]
            if action == "claim":
                return {"work": None, "action": "claim"}
            return {"work": {"id": "w1", "status": action}, "action": action}

    client = _Fake.__new__(_Fake)
    assert BrokerClient.claim_work(client, "n1")["work"] is None
    assert calls[-1] == build_compute_claim_payload("n1")
    out = BrokerClient.complete_work(client, work_id="w1", node_id="n1", result={"ok": True})
    assert out["work"]["id"] == "w1"
    assert calls[-1] == build_compute_complete_payload(
        work_id="w1", node_id="n1", result={"ok": True}
    )
    assert BrokerClient.get_work(client, "w1")["work"]["id"] == "w1"
    assert calls[-1] == build_compute_get_payload("w1")


def test_fleet_capacity_1_refuses_ssh(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    monkeypatch.setenv("NIMBUSWARE_HW_FLEET_HOSTS", "a.example")
    from hw.fleet_hardware import probe_fleet_hardware_hosts

    with patch("broker_client.capacity_bridge.try_broker_probe_dict", return_value=None):
        with pytest.raises(RuntimeError, match="CAPACITY"):
            probe_fleet_hardware_hosts()


def test_probe_remote_refuses_capacity_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from hw.probe import probe_hardware

    with pytest.raises(RuntimeError, match="CAPACITY=1"):
        probe_hardware(remote_host="a.example")


def test_miss_shape() -> None:
    assert miss("x")["via"] == "broker_miss"
