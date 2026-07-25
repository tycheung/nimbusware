from __future__ import annotations

import pytest

from broker_client.stage_bind.compute import build_compute_requeue_payload
from compute.broker_miss import broker_miss


def test_broker_miss_shape() -> None:
    out = broker_miss(error="unreachable", extra={"session_id": "s1", "enabled": True})
    assert out["via"] == "broker_miss"
    assert out["node"] is None
    assert out["error"] == "unreachable"
    assert out["session_id"] == "s1"
    assert out["enabled"] is True


def test_build_compute_requeue_payload() -> None:
    out = build_compute_requeue_payload("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    assert out == {
        "action": "requeue",
        "work_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    }


def test_node_store_refuses_under_compute_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    from compute.node_store import build_compute_node_store

    with pytest.raises(RuntimeError, match=r"COMPUTE=1\|2"):
        build_compute_node_store(None)


def test_requeue_known_action() -> None:
    from broker_client.stage_bind.compute import normalize_compute_work_payload

    out = normalize_compute_work_payload({"action": "requeue", "work_id": "x"})
    assert out["action"] == "requeue"
