from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from broker_client.client import BrokerClient
from broker_client.dual_run_route import refuse_when, require_hit
from broker_client.stage_bind.compute import build_compute_requeue_payload


def test_resolve_mesh_context_raises_under_compute_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from orchestrator.collab.pipeline_hook import resolve_mesh_context_for_run

    with patch(
        "maker.chat.session_store.build_chat_store",
        side_effect=ValueError("db down"),
    ):
        with pytest.raises(RuntimeError, match="broker_miss: resolve_mesh_context"):
            resolve_mesh_context_for_run(uuid4())


def test_platform_hardware_fit_raises_under_capacity_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from api.routes.platform_hardware import _hardware_response

    orch = MagicMock()
    orch.repo_root = "."
    with (
        patch(
            "api.routes.platform_hardware.resolve_resource_governor",
            create=True,
        ),
        patch(
            "orchestrator._pipeline.resource_governor_resolve.resolve_resource_governor",
            return_value=(
                MagicMock(
                    model_dump_public=lambda: {"tier": "medium"},
                    platform="broker",
                ),
                {"hardware_tier": "medium", "capacity_source": "broker"},
            ),
        ),
        patch(
            "api.routes.platform_hardware.governor_from_metadata",
            return_value=MagicMock(to_metadata=lambda: {}),
        ),
        patch(
            "api.routes.platform_hardware.rank_models",
            side_effect=[
                [{"tag": "a"}],
                RuntimeError("capacity_fit down"),
            ],
        ),
    ):
        with pytest.raises(RuntimeError, match="capacity_fit down"):
            _hardware_response(orch, remote_host=None, binding_id="bind-1")


def test_broker_client_terminate_restart_work(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    calls: list[dict] = []

    class _Fake(BrokerClient):
        def compute_work(self, payload: dict) -> dict:  # type: ignore[override]
            calls.append(payload)
            return {"work": {"id": "w1", "status": "queued"}, "action": "requeue"}

    client = _Fake.__new__(_Fake)
    out = BrokerClient.terminate_restart_work(client, "w1")
    assert out["work"]["id"] == "w1"
    assert calls[-1] == build_compute_requeue_payload("w1")


def test_dual_run_route_refuse_when(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from broker_client.flags import broker_compute_enabled

    with pytest.raises(RuntimeError, match="nope"):
        refuse_when(broker_compute_enabled, "nope")
    assert require_hit({"x": 1}, enabled=broker_compute_enabled, msg="m") == {"x": 1}
    with pytest.raises(RuntimeError, match="m"):
        require_hit(None, enabled=broker_compute_enabled, msg="m")


def test_worker_register_uses_broker_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from compute.worker_cli import _broker_register_node

    client = MagicMock()
    client.register_node.return_value = {
        "node": {"id": "11111111-2222-3333-4444-555555555555", "label": "h"},
    }
    with patch("broker_client.client.BrokerClient", return_value=client):
        out = _broker_register_node(host_label="h1", session_id="s1")
    assert out["node_id"] == "11111111-2222-3333-4444-555555555555"
    client.register_node.assert_called_once()


def test_parallel_critics_refuses_capacity_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from orchestrator.workflow.parallel_critics import _governor_from_resource_meta

    with patch(
        "orchestrator._pipeline.resource_governor_resolve.resolve_resource_governor",
        side_effect=RuntimeError("capacity miss"),
    ):
        with pytest.raises(RuntimeError, match="broker_miss|CAPACITY|capacity"):
            _governor_from_resource_meta(None)


def test_execute_claimed_raises_under_compute_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from compute.work_unit import WorkUnitRecord
    from compute.worker_cli import execute_claimed_work_unit

    rec = WorkUnitRecord(
        work_unit_id=uuid4(),
        run_id=uuid4(),
        session_id=None,
        stage_name="implementation",
        agent_role="implementation",
        executor_user_id="",
        status="assigned",
        payload={"mesh_assignment": True},
    )
    with (
        patch(
            "orchestrator.compute_broker_bridge.try_broker_compute_work",
            return_value=None,
        ),
        patch(
            "compute.worker_cli.execute_work_unit_on_worker",
            side_effect=AssertionError("no local"),
        ),
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            execute_claimed_work_unit(rec)
