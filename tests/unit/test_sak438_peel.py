from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest

from compute.broker_session_status import (
    assert_broker_compute_ok,
    assert_broker_compute_record_ok,
    broker_session_compute_status,
)


def test_assert_raises_on_error_plus_empty_list() -> None:
    """sak438-a: error + nodes=[] is a miss (not empty success)."""
    with pytest.raises(RuntimeError, match="broker_miss"):
        assert_broker_compute_ok(
            {"error": "down", "nodes": []},
            feature="nodes",
            list_key="nodes",
        )


def test_assert_raises_on_error_plus_empty_work() -> None:
    with pytest.raises(RuntimeError, match="broker_miss"):
        assert_broker_compute_ok(
            {"error": "down", "work": []},
            feature="work",
            list_key="work",
        )


def test_assert_allows_empty_list_without_error() -> None:
    out = assert_broker_compute_ok(
        {"nodes": []},
        feature="nodes",
        list_key="nodes",
    )
    assert out["nodes"] == []


def test_assert_record_ok_raises_on_error_dict() -> None:
    with pytest.raises(RuntimeError, match="broker_miss"):
        assert_broker_compute_record_ok(
            {"error": "reg failed", "node": None},
            feature="register",
            record_key="node",
        )


def test_assert_record_ok_raises_on_via_broker_miss() -> None:
    """sak487-i: via=broker_miss without error is a write-path miss."""
    with pytest.raises(RuntimeError, match="broker_miss"):
        assert_broker_compute_record_ok(
            {"via": "broker_miss", "status": "degraded", "feature": "enqueue"},
            feature="enqueue",
            record_key="work",
        )


def test_session_status_error_empty_list_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with patch(
        "broker_client.stage_bind.compute.compute_node_via_broker",
        return_value={"error": "nodes down", "nodes": []},
    ):
        with pytest.raises(RuntimeError, match="nodes down"):
            broker_session_compute_status("s1", feature="fleet_mesh")


def test_parallel_writer_refuses_missing_ram(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from broker_client.stage_bind.capacity import parallel_writer_stages_from_capacity

    with pytest.raises(RuntimeError, match="ram_probe_unavailable"):
        parallel_writer_stages_from_capacity({"snapshot": {}})


def test_mesh_host_sync_list_uses_assert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from compute.mesh_host_sync import _broker_list_units

    with patch(
        "broker_client.stage_bind.compute.compute_work_via_broker",
        return_value={"error": "list down", "work": []},
    ):
        with pytest.raises(RuntimeError, match="list down"):
            _broker_list_units(uuid4())


def test_capacity_route_single_map_helper() -> None:
    from hw import capacity_route as cr

    # sak438-c: no duplicate def (second would overwrite identically — ensure callable once).
    assert callable(cr.map_broker_capacity_http_error)
    with pytest.raises(RuntimeError, match="CAPACITY"):
        cr.map_broker_capacity_http_error(RuntimeError("x"), feature="soak")
