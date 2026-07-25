from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from compute.mesh_event_replay import replay_events_to_store, replay_events_to_store_absorb
from compute.mesh_workspace_merge import apply_workspace_files, apply_workspace_files_absorb
from hw.fleet_hardware import probe_fleet_hardware_hosts


def test_absorb_helpers_allowed_under_compute_2(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    store = MagicMock()
    store.list_run_events.return_value = []
    with pytest.raises(RuntimeError, match=r"COMPUTE=1\|2"):
        replay_events_to_store(store, uuid4(), [])
    with pytest.raises(RuntimeError, match=r"COMPUTE=1\|2"):
        apply_workspace_files(tmp_path, {})
    assert replay_events_to_store_absorb(store, uuid4(), []) == 0
    assert apply_workspace_files_absorb(tmp_path, {}) == []


def test_capacity_1_fleet_hosts_prefer_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    monkeypatch.setenv("NIMBUSWARE_HW_FLEET_HOSTS", "a.example,b.example")
    with patch(
        "broker_client.capacity_bridge.try_broker_probe_dict",
        return_value={
            "tier": "medium",
            "ram_total_gb": 16.0,
            "ram_available_gb": 8.0,
            "cpu_count": 4,
            "gpus": [],
            "gpu_groups": [],
            "unified_memory": False,
            "errors": [],
            "platform": "broker",
        },
    ):
        out = probe_fleet_hardware_hosts()
    assert out["capacity_source"] == "broker"
    assert out["host_count"] == 1
    assert out["hosts"][0]["host"] == "local-broker"
