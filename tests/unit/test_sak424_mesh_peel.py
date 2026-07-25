from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from compute.mesh_host_sync import absorb_completed_mesh_units
from orchestrator.role_claims_mesh import (
    caps_dict_from_broker_node,
    user_id_from_broker_node,
)


def test_user_id_from_broker_node_label_and_caps() -> None:
    assert user_id_from_broker_node({"label": "user:alice"}) == "alice"
    assert user_id_from_broker_node({"caps": ["mesh_worker", "user:bob"]}) == "bob"
    assert user_id_from_broker_node({"caps": ["user_id=carol"]}) == "carol"
    assert user_id_from_broker_node({"user_id": "dave"}) == "dave"
    assert user_id_from_broker_node({"label": "worker"}) == ""


def test_caps_dict_from_broker_node_skips_user() -> None:
    out = caps_dict_from_broker_node({"caps": ["mesh_worker", "user:alice", "tier=strong"]})
    assert out["mesh_worker"] is True
    assert out["tier"] == "strong"
    assert "user:alice" not in out


def test_absorb_completed_mesh_units_broker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    run_id = uuid4()
    store = MagicMock()
    store.list_run_events.return_value = []

    unit = {
        "kind": "implementation",
        "status": "completed",
        "payload": {"run_id": str(run_id), "stage_name": "implementation"},
        "result": {
            "replay_events": [],
            "workspace_files": {"a.txt": "hello"},
            "verifier_exit_code": 0,
        },
    }

    with (
        patch(
            "compute.mesh_host_sync._broker_list_units",
            return_value=[unit],
        ),
        patch(
            "compute.mesh_event_replay.replay_events_to_store_absorb",
            return_value=0,
        ) as replay,
        patch(
            "compute.mesh_workspace_merge.apply_workspace_files_absorb",
            return_value=["a.txt"],
        ) as apply,
    ):
        out = absorb_completed_mesh_units(
            store,
            run_id,
            ["implementation"],
            host_workspace=tmp_path,
        )
    assert out["files_merged"] == 1
    assert out["events_replayed"] == 0
    apply.assert_called_once()
    replay.assert_called_once()


def test_worker_uses_broker_when_compute_1_and_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    monkeypatch.delenv("NIMBUSWARE_BROKER_HTTP", raising=False)
    from compute.worker_cli import run_worker_loop

    with (
        patch(
            "compute.worker_cli._broker_register_node",
            return_value={"node_id": "11111111-2222-3333-4444-555555555555"},
        ) as reg,
        patch(
            "compute.worker_cli._broker_heartbeat_node",
            return_value={"node_id": "11111111-2222-3333-4444-555555555555"},
        ),
        patch("compute.worker_cli._broker_claim_execute_complete", return_value=False),
        patch("compute.worker_cli.time.sleep", return_value=None),
    ):
        code = run_worker_loop(
            host_url="http://unused",
            session_token="",
            host_label="w",
            worker_base_url="http://127.0.0.1:0",
            session_id="s1",
            interval_seconds=0.0,
            max_heartbeats=1,
            pull_work_units=True,
        )
    assert code == 0
    reg.assert_called_once()


def test_broker_client_list_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_HTTP", "http://127.0.0.1:9")
    from broker_client.client import BrokerClient

    client = BrokerClient(base_url="http://127.0.0.1:9")
    with patch.object(client, "compute_work", return_value={"work": []}) as work:
        out = client.list_work_filtered(run_id="r1", stage_name="implementation")
    assert out == {"work": []}
    assert work.call_args[0][0]["action"] == "list"
    with patch.object(client, "compute_nodes", return_value={"nodes": []}) as nodes:
        out2 = client.list_nodes_filtered(session_id="s1")
    assert out2 == {"nodes": []}
    assert nodes.call_args[0][0]["session_id"] == "s1"
