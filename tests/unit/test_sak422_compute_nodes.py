from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from broker_client.stage_bind.compute import (
    build_compute_register_payload,
    compute_node_via_broker,
    node_id_from_broker_record,
)
from compute.work_unit import get_work_unit_queue
from compute.worker_cli import _broker_heartbeat_node, _broker_register_node
from hw.fleet_hardware import probe_fleet_hardware_hosts


def test_compute_node_via_broker_http_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    monkeypatch.setenv("NIMBUSWARE_BROKER_HTTP", "http://127.0.0.1:9")
    http = MagicMock()
    http.compute_nodes.return_value = {
        "node": {"id": "11111111-2222-3333-4444-555555555555", "label": "w"},
        "action": "register",
        "backend": "memory",
    }
    out = compute_node_via_broker(
        build_compute_register_payload("w", caps=["mesh_worker"]),
        http=http,
    )
    assert node_id_from_broker_record(out["node"]).startswith("11111111")
    http.compute_nodes.assert_called_once()


def test_broker_register_and_heartbeat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    nid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    calls: list[dict] = []

    def _via(payload: dict, **_kwargs: object) -> dict:
        calls.append(payload)
        if payload.get("action") == "register":
            return {"node": {"id": nid, "label": payload["label"]}, "action": "register"}
        if payload.get("action") == "heartbeat":
            return {"node": {"id": nid, "label": "w"}, "action": "heartbeat"}
        return {"error": "unexpected"}

    with patch(
        "broker_client.stage_bind.compute.compute_node_via_broker",
        side_effect=_via,
    ):
        node = _broker_register_node(host_label="worker-a", capabilities={"gpu": True})
        assert node["node_id"] == nid
        beat = _broker_heartbeat_node(nid)
        assert beat["node_id"] == nid
    assert any(c.get("action") == "register" for c in calls)
    assert any(c.get("action") == "heartbeat" for c in calls)


def test_get_work_unit_queue_refuses_under_compute_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    with pytest.raises(RuntimeError, match=r"COMPUTE=1\|2"):
        get_work_unit_queue()


def test_fleet_hardware_capacity_2_hosts_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "2")
    monkeypatch.setenv("NIMBUSWARE_HW_FLEET_HOSTS", "a.example,b.example")
    with patch("hw.fleet_hardware._local_broker_row", return_value=None):
        with pytest.raises(RuntimeError, match="CAPACITY"):
            probe_fleet_hardware_hosts()


def test_pipeline_hook_refuse_local_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    from orchestrator.collab.pipeline_hook import mesh_assign_parallel_stages

    run_id = uuid4()
    session_id = uuid4()
    node_id = uuid4()

    with (
        patch("orchestrator.collab.pipeline_hook.get_mesh_scheduler") as sched_mod,
        patch(
            "orchestrator.compute_broker_bridge.try_broker_compute_work",
            return_value=None,
        ),
        patch("env.find_repo_root", return_value="."),
        patch(
            "maker.user_agent_overlay.prompt_extension_for_taxonomy_key",
            return_value="",
        ),
        patch(
            "orchestrator.collab.mesh_bindings.executor_binding_hint",
            return_value=None,
        ),
    ):
        sched = MagicMock()
        sched.assign.return_value = {"implementation": node_id}
        sched_mod.return_value = sched
        with pytest.raises(RuntimeError, match="queue.enqueue"):
            mesh_assign_parallel_stages(
                run_id=run_id,
                stage_names=["implementation"],
                session_id=session_id,
                workload_distribution="mesh",
                node_ids=[node_id],
            )
