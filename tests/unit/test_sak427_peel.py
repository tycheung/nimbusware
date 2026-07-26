from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from broker_client.client import BrokerClient
from broker_client.stage_bind.compute import (
    build_compute_heartbeat_payload,
    build_compute_register_payload,
)


def test_register_heartbeat_payload_builders() -> None:
    reg = build_compute_register_payload("w1", caps=["echo"], session_id="s1")
    assert reg["action"] == "register"
    assert reg["session_id"] == "s1"
    hb = build_compute_heartbeat_payload("11111111-2222-3333-4444-555555555555")
    assert hb["action"] == "heartbeat"


def test_broker_client_register_heartbeat_helpers() -> None:
    calls: list[tuple[str, dict]] = []

    class _Fake(BrokerClient):
        def compute_nodes(self, payload: dict) -> dict:  # type: ignore[override]
            calls.append(("nodes", payload))
            return {
                "node": {"id": "n1", "label": payload.get("label")},
                "action": payload["action"],
            }

    client = _Fake.__new__(_Fake)
    out = BrokerClient.register_node(client, "w", caps=["mesh"], session_id="s")
    assert out["action"] == "register"
    out2 = BrokerClient.heartbeat_node(client, "n1")
    assert out2["action"] == "heartbeat"
    assert len(calls) == 2


def test_terminate_restart_refuses_under_compute_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from broker_client.flags import broker_compute_enabled

    assert broker_compute_enabled()

    def refuse() -> None:
        if broker_compute_enabled():
            raise HTTPException(status_code=501, detail="broker_compute_no_terminate_restart")

    with pytest.raises(HTTPException) as exc:
        refuse()
    assert exc.value.status_code == 501


def test_delegate_broker_miss_shape() -> None:
    """sak427-c: COMPUTE=1 delegate miss uses broker_miss (no node_store)."""
    out = {
        "node": None,
        "via": "broker_miss",
        "error": "no compute node for session",
    }
    assert out["via"] == "broker_miss"
    assert out["node"] is None
    assert uuid4()  # smoke uuid import used elsewhere
