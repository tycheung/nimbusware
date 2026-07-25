from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from compute.node_store import build_compute_node_store
from compute.work_unit import InMemoryWorkUnitQueue, get_work_unit_queue
from hw.capacity_route import CAPACITY_EXCLUSIVE_MSG, refuse_legacy, require_hit


def test_queue_refuses_compute_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with pytest.raises(RuntimeError, match=r"COMPUTE=1\|2"):
        get_work_unit_queue()


def test_node_store_refuses_compute_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with pytest.raises(RuntimeError, match=r"COMPUTE=1\|2"):
        build_compute_node_store(None)


def test_terminate_restart_refuses_compute_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    queue = InMemoryWorkUnitQueue()
    with pytest.raises(RuntimeError, match=r"COMPUTE=1\|2"):
        queue.terminate_restart(uuid4())


def test_cache_refuses_capacity_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    import hw.cache as cache_mod
    from hw.cache import get_cached_profile

    cache_mod._broker_cached = None
    with patch("broker_client.capacity_bridge.try_broker_probe_dict", return_value=None):
        with pytest.raises(RuntimeError, match=r"CAPACITY=1\|2"):
            get_cached_profile(fresh=True)


def test_governor_refuses_capacity_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from hw.governor import governor_for_profile
    from hw.profile import profile_from_probe

    weak = profile_from_probe(
        {
            "tier": "weak",
            "ram_total_gb": 4.0,
            "ram_available_gb": 2.0,
            "cpu_count": 2,
            "gpus": [],
            "gpu_groups": [],
            "unified_memory": False,
            "errors": [],
            "platform": "test",
        }
    )
    with patch("broker_client.capacity_bridge.try_broker_capacity_probe", return_value=None):
        with pytest.raises(RuntimeError, match=r"CAPACITY=1\|2"):
            governor_for_profile(weak)


def test_pressure_refuses_capacity_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from hw.pressure import sample_pressure

    with patch(
        "broker_client.capacity_bridge.try_broker_capacity_pressure",
        return_value=None,
    ):
        with pytest.raises(RuntimeError, match=r"CAPACITY=1\|2"):
            sample_pressure()


def test_fit_refuses_capacity_1_on_probe_miss(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from hw.fit import rank_models
    from hw.profile import profile_from_probe

    weak = profile_from_probe(
        {
            "tier": "weak",
            "ram_total_gb": 4.0,
            "ram_available_gb": 2.0,
            "cpu_count": 2,
            "gpus": [],
            "gpu_groups": [],
            "unified_memory": False,
            "errors": [],
            "platform": "test",
        }
    )
    with patch("broker_client.capacity_bridge.try_broker_probe_dict", return_value=None):
        with pytest.raises(RuntimeError, match=r"CAPACITY=1\|2"):
            rank_models(tmp_path, weak)


def test_minimal_worker_refuses_capacity_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from compute.minimal_worker import probe_minimal_worker_capabilities

    with patch("broker_client.capacity_bridge.try_broker_probe_dict", return_value=None):
        with pytest.raises(RuntimeError, match=r"CAPACITY=1\|2"):
            probe_minimal_worker_capabilities()


def test_resource_governor_resolve_refuses_capacity_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from orchestrator._pipeline.resource_governor_resolve import resolve_resource_governor

    with patch(
        "orchestrator._pipeline.resource_governor_resolve.try_broker_capacity_probe",
        return_value=None,
    ):
        with pytest.raises(RuntimeError, match=r"CAPACITY=1\|2"):
            resolve_resource_governor()


def test_capacity_route_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    with pytest.raises(RuntimeError, match="CAPACITY"):
        refuse_legacy()
    assert require_hit({"ok": True}) == {"ok": True}
    with pytest.raises(RuntimeError, match="CAPACITY"):
        require_hit(None)
    assert CAPACITY_EXCLUSIVE_MSG


def test_worker_cli_uses_broker_client_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from compute.worker_cli import _broker_claim_execute_complete

    client = MagicMock()
    client.claim_work.return_value = {
        "work": {"id": "w1", "kind": "echo", "payload": {}},
    }
    client.complete_work.return_value = {"ok": True}
    with (
        patch("broker_client.client.BrokerClient", return_value=client),
        patch(
            "orchestrator.compute_broker_bridge.try_broker_compute_work",
            return_value={"ok": True},
        ),
    ):
        assert _broker_claim_execute_complete("n1") is True
    client.claim_work.assert_called_once_with("n1")
    client.complete_work.assert_called_once()
