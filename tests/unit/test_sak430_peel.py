from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from broker_client.stage_bind.compute import (
    build_compute_requeue_payload,
    terminate_restart_via_broker,
)
from compute.mesh_host_sync import wait_for_mesh_units
from compute.work_unit import InMemoryWorkUnitQueue


def test_wait_for_mesh_units_broker_first_under_compute_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    run_id = uuid4()
    calls: list[dict] = []

    def _fake(payload: dict) -> dict:
        calls.append(payload)
        return {
            "work": [
                {
                    "kind": "implementation",
                    "status": "completed",
                    "payload": {"stage_name": "implementation"},
                    "result": {},
                }
            ]
        }

    with (
        patch(
            "broker_client.stage_bind.compute.compute_work_via_broker",
            side_effect=_fake,
        ),
        patch("compute.mesh_host_sync.mesh_poll_interval_seconds", return_value=0.01),
        patch("compute.mesh_host_sync.mesh_wait_timeout_seconds", return_value=2.0),
    ):
        assert wait_for_mesh_units(run_id, ["implementation"]) is True
    assert calls


def test_wait_raises_on_broker_miss_under_compute_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak432-b: COMPUTE=1 broker miss does not fall back to legacy."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    run_id = uuid4()

    with patch(
        "broker_client.stage_bind.compute.compute_work_via_broker",
        side_effect=RuntimeError("broker down"),
    ):
        with pytest.raises(RuntimeError, match="broker"):
            wait_for_mesh_units(run_id, ["implementation"], timeout_seconds=0.1)


def test_delegate_control_exclusivity_shape() -> None:
    """sak430-b: COMPUTE enabled never falls to node_store (shape)."""
    from compute.broker_miss import broker_miss

    out = broker_miss(error="delegate-control broker path exhausted")
    assert out["via"] == "broker_miss"
    assert "node" not in out or out.get("node") is None


def test_terminate_restart_via_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    calls: list[dict] = []

    with patch(
        "broker_client.stage_bind.compute.compute_work_via_broker",
        side_effect=lambda payload, **_: (
            calls.append(payload)
            or {
                "work": {"id": payload["work_id"], "status": "queued"},
                "action": "requeue",
            }
        ),
    ):
        out = terminate_restart_via_broker("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    assert out["action"] == "requeue"
    assert calls[0] == build_compute_requeue_payload("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def test_inmemory_terminate_restart_refuses_compute_2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    queue = InMemoryWorkUnitQueue()
    with pytest.raises(RuntimeError, match=r"COMPUTE=1\|2"):
        queue.terminate_restart(uuid4())


def test_fleet_mesh_queue_depth_session_filter() -> None:
    from broker_client.stage_bind.compute import queue_depth_for_session

    sid = str(uuid4())
    other = str(uuid4())
    items = [
        {"status": "queued", "payload": {"session_id": sid}},
        {"status": "queued", "payload": {"session_id": other}},
        {"status": "queued", "payload": {}},
    ]
    assert queue_depth_for_session(items, sid) == 1
    assert queue_depth_for_session(items, None) == 3


def test_rank_models_capacity_fit_when_binding(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from hw.fit import rank_models
    from hw.profile import HardwareProfile

    profile = HardwareProfile(tier="weak", platform="test")
    candidates = [{"tag": "tiny", "vram_gb": 1}]

    with patch(
        "broker_client.stage_bind.capacity.capacity_fit_via_broker",
        return_value={"ranked": [{"tag": "tiny", "level": "good"}]},
    ):
        out = rank_models(
            tmp_path,
            profile,
            binding_id="bind-1",
            candidates=candidates,
        )
    assert out == [{"tag": "tiny", "level": "good"}]
