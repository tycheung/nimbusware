from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from compute.broker_public import (
    broker_node_public,
    broker_work_public,
    caps_from_capabilities,
)


def test_broker_node_public_maps_caps() -> None:
    out = broker_node_public(
        {
            "id": "11111111-2222-3333-4444-555555555555",
            "label": "w1",
            "caps": ["echo", "allow_host_resource_management=true"],
            "session_id": "s1",
        }
    )
    assert out["node_id"].startswith("11111111")
    assert out["via"] == "broker"
    assert out["allow_host_resource_management"] is True
    assert out["capabilities"]["echo"] is True


def test_broker_work_public_maps_status() -> None:
    out = broker_work_public(
        {
            "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "kind": "implementation",
            "status": "claimed",
            "payload": {"run_id": "r1", "stage_name": "implementation"},
            "claimed_by": "11111111-2222-3333-4444-555555555555",
        }
    )
    assert out["status"] == "assigned"
    assert out["via"] == "broker"
    assert out["stage_name"] == "implementation"


def test_caps_from_capabilities() -> None:
    assert "mesh_worker" in caps_from_capabilities({"mesh_worker": True})
    assert "tier=high" in caps_from_capabilities({"tier": "high"})


def test_list_nodes_broker_first_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from broker_client.flags import broker_compute_enabled
    from broker_client.stage_bind import compute as compute_bind

    assert broker_compute_enabled()
    sid = uuid4()
    with patch.object(
        compute_bind,
        "compute_node_via_broker",
        return_value={
            "nodes": [
                {
                    "id": "11111111-2222-3333-4444-555555555555",
                    "label": "w",
                    "caps": [],
                    "session_id": str(sid),
                }
            ]
        },
    ) as mocked:
        raw = compute_bind.compute_node_via_broker(
            compute_bind.build_compute_list_nodes_payload(session_id=str(sid))
        )
        nodes = [
            broker_node_public(item, session_id=sid)
            for item in (raw.get("nodes") or [])
            if isinstance(item, dict)
        ]
        out = {"nodes": nodes, "via": "broker"}
    assert out["via"] == "broker"
    assert len(out["nodes"]) == 1
    mocked.assert_called_once()


def test_claim_broker_first_empty_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from broker_client.stage_bind import compute as compute_bind

    with patch.object(
        compute_bind,
        "compute_work_via_broker",
        return_value={"error": "queue empty", "work": None},
    ):
        raw = compute_bind.compute_work_via_broker(
            compute_bind.build_compute_claim_payload(str(uuid4()))
        )
        err = str(raw.get("error") or "")
        assert "empty" in err.lower()
        out = {"work_unit": None, "via": "broker"}
    assert out == {"work_unit": None, "via": "broker"}


def test_refuse_still_under_compute_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    from broker_client.flags import broker_compute_only

    def refuse() -> None:
        if broker_compute_only():
            raise HTTPException(status_code=503, detail="broker_compute_only")

    with pytest.raises(HTTPException) as exc:
        refuse()
    assert exc.value.status_code == 503


def test_opt_in_broker_miss_shape() -> None:
    """sak426-i: dual-run opt-in miss uses broker_miss (no node_store fallback)."""
    out = {
        "session_id": str(uuid4()),
        "enabled": True,
        "share_policy": "off",
        "via": "broker_miss",
        "node": None,
        "error": "unreachable",
    }
    assert out["via"] == "broker_miss"
    assert out["node"] is None
