from __future__ import annotations

from unittest.mock import patch

import pytest

from compute.minimal_worker import probe_minimal_worker_capabilities
from compute.worker_cli import _broker_claim_execute_complete


def test_minimal_worker_broker_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    with patch(
        "broker_client.capacity_bridge.try_broker_probe_dict",
        return_value={
            "tier": "strong",
            "ram_total_gb": 32.0,
            "ram_available_gb": 16.0,
            "cpu_count": 8,
            "gpus": [],
            "gpu_groups": [],
            "unified_memory": False,
            "errors": [],
            "platform": "broker_capacity",
            "broker_capacity": True,
        },
    ):
        caps = probe_minimal_worker_capabilities()
    assert caps["hardware_tier"] == "strong"
    assert caps["capacity_source"] == "broker"


def test_minimal_worker_capacity_only_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "2")
    with patch(
        "broker_client.capacity_bridge.try_broker_probe_dict",
        return_value=None,
    ):
        with pytest.raises(RuntimeError, match=r"CAPACITY=1\|2"):
            probe_minimal_worker_capabilities()


def test_broker_claim_execute_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    calls: list[dict] = []

    class _FakeClient:
        def claim_work(self, node_id: str) -> dict:
            calls.append({"action": "claim", "node_id": node_id})
            return {
                "work": {
                    "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                    "kind": "echo",
                    "payload": {},
                }
            }

        def complete_work(
            self,
            *,
            work_id: str,
            node_id: str,
            result: dict | None = None,
        ) -> dict:
            calls.append(
                {
                    "action": "complete",
                    "work_id": work_id,
                    "node_id": node_id,
                    "result": result,
                }
            )
            return {"work": {"id": work_id, "status": "completed"}}

    with (
        patch("broker_client.client.BrokerClient", return_value=_FakeClient()),
        patch(
            "orchestrator.compute_broker_bridge.try_broker_compute_work",
            return_value={"ok": True, "via": "broker"},
        ),
    ):
        assert _broker_claim_execute_complete("11111111-2222-3333-4444-555555555555") is True
    assert any(c.get("action") == "claim" for c in calls)
    assert any(c.get("action") == "complete" for c in calls)
