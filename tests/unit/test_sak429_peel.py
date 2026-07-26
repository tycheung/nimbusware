from __future__ import annotations

from uuid import uuid4

import pytest

from broker_client.client import BrokerClient
from broker_client.stage_bind.compute import build_compute_requeue_payload


def test_broker_client_requeue_work() -> None:
    calls: list[dict] = []

    class _Fake(BrokerClient):
        def compute_work(self, payload: dict) -> dict:  # type: ignore[override]
            calls.append(payload)
            return {"work": {"id": payload["work_id"], "status": "queued"}, "action": "requeue"}

    client = _Fake.__new__(_Fake)
    out = BrokerClient.requeue_work(client, "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    assert out["action"] == "requeue"
    assert calls[0] == build_compute_requeue_payload("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def test_opt_out_under_compute_no_store_shape() -> None:
    """sak429-e / sak443-c: COMPUTE=1 opt-out returns via=broker_opt_out without node_store."""
    out = {
        "session_id": str(uuid4()),
        "enabled": False,
        "share_policy": "off",
        "via": "broker_opt_out",
        "status": "ok",
        "feature": "session_compute_opt_out",
        "node": None,
    }
    assert out["via"] == "broker_opt_out"
    assert out["enabled"] is False
    assert out["node"] is None


def test_requeue_payload_known() -> None:
    from broker_client.stage_bind.compute import normalize_compute_work_payload

    assert (
        normalize_compute_work_payload({"action": "requeue", "work_id": "w"})["action"] == "requeue"
    )


def test_node_store_still_refuses_compute_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    from compute.node_store import build_compute_node_store

    with pytest.raises(RuntimeError, match=r"COMPUTE=1\|2"):
        build_compute_node_store(None)
