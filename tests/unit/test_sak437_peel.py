from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from broker_client.client import BrokerClient
from compute.broker_route import map_broker_chat_compute_miss
from compute.broker_session_status import (
    assert_broker_compute_ok,
    broker_session_compute_status,
)


def test_assert_broker_compute_ok_raises_on_error_dict() -> None:
    with pytest.raises(RuntimeError, match="broker_miss"):
        assert_broker_compute_ok(
            {"error": "down", "nodes": None},
            feature="nodes",
            list_key="nodes",
        )


def test_assert_broker_compute_ok_allows_empty_list() -> None:
    out = assert_broker_compute_ok(
        {"nodes": []},
        feature="nodes",
        list_key="nodes",
    )
    assert out["nodes"] == []


def test_broker_session_status_error_dict_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with patch(
        "broker_client.stage_bind.compute.compute_node_via_broker",
        return_value={"error": "nodes down"},
    ):
        with pytest.raises(RuntimeError, match="nodes down"):
            broker_session_compute_status("s1", feature="fleet_mesh")


def test_map_broker_chat_compute_miss_under_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    out = map_broker_chat_compute_miss(
        "no node",
        feature="delegate_control",
    )
    assert out["via"] == "broker_miss"
    assert out["feature"] == "delegate_control"


def test_capacity_pressure_refuses_missing_ram(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from broker_client.stage_bind.capacity import pressure_from_capacity_probe

    with pytest.raises(RuntimeError, match="ram_probe_unavailable"):
        pressure_from_capacity_probe({"snapshot": {}})


def test_capacity_probe_dict_refuses_missing_ram(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from broker_client.stage_bind.capacity import probe_dict_from_capacity

    with pytest.raises(RuntimeError, match="ram_probe_unavailable"):
        probe_dict_from_capacity({"snapshot": {}})


def test_capacity_probe_via_broker_error_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from broker_client.stage_bind import capacity as cap

    http = MagicMock()
    http.capacity.return_value = {"error": "probe down"}
    with pytest.raises(RuntimeError, match="probe down"):
        cap.capacity_probe_via_broker(client=http)


def test_broker_client_queue_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    client = BrokerClient(base_url="http://broker.test")
    with patch.object(
        client,
        "list_work_filtered",
        return_value={"work": [{"status": "queued", "session_id": "s1"}]},
    ):
        out = client.queue_depth("s1")
    assert out["queued"] == 1
    assert out["via"] == "broker"
