from __future__ import annotations

from unittest.mock import patch

import pytest

from broker_client.capacity_bridge import try_broker_capacity_probe
from broker_client.compute_bridge import try_broker_compute_work
from compute.broker_session_status import broker_session_compute_status
from compute.minimal_worker import probe_minimal_worker_capabilities
from hw.fleet_hardware import run_probe_matrix


def test_compute_bridge_reraises_under_compute_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    import broker_client.compute_bridge as bridge_mod

    monkeypatch.setattr(
        bridge_mod,
        "compute_work_via_broker",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("down")),
    )
    with pytest.raises(RuntimeError, match="down"):
        try_broker_compute_work({"kind": "echo"})


def test_capacity_bridge_reraises_under_capacity_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    import broker_client.capacity_bridge as bridge_mod

    monkeypatch.setattr(
        bridge_mod,
        "capacity_probe_via_broker",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("down")),
    )
    with pytest.raises(RuntimeError, match="down"):
        try_broker_capacity_probe()


def test_broker_session_status_propagates_queue_miss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    nid = "11111111-2222-3333-4444-555555555555"
    with (
        patch(
            "broker_client.stage_bind.compute.compute_node_via_broker",
            return_value={"nodes": [{"id": nid, "label": "n1", "caps": ["mesh"]}]},
        ),
        patch(
            "broker_client.stage_bind.compute.compute_work_via_broker",
            side_effect=RuntimeError("work list down"),
        ),
    ):
        out = broker_session_compute_status("s1", feature="fleet_mesh")
    assert out["via"] == "broker_miss"
    assert out["status"] == "degraded"
    assert out["queue_depth"] == 0
    assert out["nodes"][0]["node_id"] == nid
    assert "work list down" in str(out.get("error") or "")


def test_broker_session_status_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    nid = "11111111-2222-3333-4444-555555555555"
    with (
        patch(
            "broker_client.stage_bind.compute.compute_node_via_broker",
            return_value={"nodes": [{"id": nid, "label": "n1", "caps": ["mesh"]}]},
        ),
        patch(
            "broker_client.stage_bind.compute.compute_work_via_broker",
            return_value={"work": [{"status": "queued", "session_id": "s1"}]},
        ),
    ):
        out = broker_session_compute_status("s1", feature="fleet_mesh")
    assert out["via"] == "broker"
    assert out["feature"] == "fleet_mesh"
    assert out["queue_depth"] == 1
    assert out["nodes"][0]["node_id"] == nid


def test_run_probe_matrix_refuses_capacity_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    monkeypatch.setenv("NIMBUSWARE_HW_FLEET_HOSTS", "a.example")
    with pytest.raises(RuntimeError, match=r"CAPACITY=1\|2"):
        run_probe_matrix()


def test_minimal_worker_non_runtime_raises_under_capacity_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    with patch(
        "broker_client.capacity_bridge.try_broker_probe_dict",
        side_effect=ValueError("weird"),
    ):
        with pytest.raises(RuntimeError, match="CAPACITY"):
            probe_minimal_worker_capabilities()
