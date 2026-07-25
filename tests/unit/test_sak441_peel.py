from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest

from compute.broker_session_status import assert_broker_compute_ok


def test_assert_list_key_null_is_miss() -> None:
    """sak441-a: work/nodes null is a miss (no silent [])."""
    with pytest.raises(RuntimeError, match="non-list key"):
        assert_broker_compute_ok({"work": None}, feature="mesh", list_key="work")
    out = assert_broker_compute_ok({"work": []}, feature="mesh", list_key="work")
    assert out["work"] == []


def test_mesh_list_null_work_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from compute.mesh_host_sync import _broker_list_units

    with patch(
        "broker_client.stage_bind.compute.compute_work_via_broker",
        return_value={"work": None},
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            _broker_list_units(uuid4())


def test_worker_loop_exits_on_broker_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from compute import worker_cli as wc

    with (
        patch.object(
            wc,
            "_broker_register_node",
            return_value={"node_id": "n1"},
        ),
        patch.object(
            wc,
            "_broker_heartbeat_node",
            side_effect=RuntimeError("broker_miss: heartbeat down"),
        ),
    ):
        code = wc.run_worker_loop(
            host_url="http://x",
            session_token="t",
            host_label="h",
            worker_base_url="http://w",
            session_id="s",
            interval_seconds=0.0,
            max_heartbeats=1,
            pull_work_units=False,
        )
    assert code == 1


def test_capacity_http_miss_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from hw.capacity_route import map_broker_capacity_http_miss

    body = map_broker_capacity_http_miss(
        RuntimeError("probe down"),
        feature="platform_hardware",
    )
    assert body["capacity_source"] == "broker_miss"
    assert body["status"] == "degraded"
    assert body["via"] == "broker_miss"


def test_node_id_from_broker_node_match() -> None:
    from compute.broker_node_match import node_id_from_broker_record

    assert node_id_from_broker_record({"id": "a"}) == "a"
    assert node_id_from_broker_record({"node_id": "b"}) == "b"
    assert node_id_from_broker_record(None) == ""
