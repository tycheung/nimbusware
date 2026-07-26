from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from compute.work_unit import WorkUnitRecord, get_work_unit_queue
from compute.worker_cli import execute_claimed_work_unit
from orchestrator.collab.pipeline_hook import mesh_assign_parallel_stages


def _sample_rec() -> WorkUnitRecord:
    return WorkUnitRecord(
        work_unit_id=uuid4(),
        run_id=uuid4(),
        session_id=uuid4(),
        stage_name="implementation",
        agent_role="implementation",
        executor_user_id="",
        status="assigned",
        payload={"mesh_assignment": True},
        node_id=uuid4(),
    )


def test_pipeline_hook_flag_off_still_enqueues(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_COMPUTE", raising=False)
    sid = uuid4()
    run_id = uuid4()
    n1 = uuid4()
    mesh_assign_parallel_stages(
        run_id=run_id,
        stage_names=["implementation"],
        session_id=sid,
        workload_distribution="auto_share",
        node_ids=[n1],
        workspace=tmp_path,
    )
    units = get_work_unit_queue().list_units(run_id=run_id)
    assert len(units) == 1
    assert units[0].stage_name == "implementation"


def test_pipeline_hook_flag_on_broker_hit_skips_enqueue(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    sid = uuid4()
    run_id = uuid4()
    n1 = uuid4()
    with patch(
        "orchestrator.compute_broker_bridge.try_broker_compute_work",
        return_value={"work": {"id": "w-broker"}, "via": "broker"},
    ) as mock_bridge:
        mesh_assign_parallel_stages(
            run_id=run_id,
            stage_names=["implementation"],
            session_id=sid,
            workload_distribution="auto_share",
            node_ids=[n1],
            workspace=tmp_path,
        )
    mock_bridge.assert_called_once()
    with pytest.raises(RuntimeError, match=r"COMPUTE=1\|2"):
        get_work_unit_queue()


def test_pipeline_hook_flag_on_broker_none_refuses_local(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sak431-c: COMPUTE=1 broker miss does not fall back to local enqueue."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    sid = uuid4()
    run_id = uuid4()
    n1 = uuid4()
    with patch(
        "orchestrator.compute_broker_bridge.try_broker_compute_work",
        return_value=None,
    ):
        with pytest.raises(RuntimeError, match="queue.enqueue"):
            mesh_assign_parallel_stages(
                run_id=run_id,
                stage_names=["implementation"],
                session_id=sid,
                workload_distribution="auto_share",
                node_ids=[n1],
                workspace=tmp_path,
            )
    with pytest.raises(RuntimeError, match=r"COMPUTE=1\|2"):
        get_work_unit_queue()


def test_worker_flag_off_uses_local_execute(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_COMPUTE", raising=False)
    rec = _sample_rec()
    local = {"ok": True, "via": "local"}
    with patch(
        "compute.worker_cli.execute_work_unit_on_worker",
        return_value=local,
    ) as mock_local:
        out = execute_claimed_work_unit(rec)
    mock_local.assert_called_once_with(rec)
    assert out == local


def test_worker_flag_on_broker_hit_skips_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    rec = _sample_rec()
    broker = {"ok": True, "via": "broker"}
    with (
        patch(
            "orchestrator.compute_broker_bridge.try_broker_compute_work",
            return_value=broker,
        ) as mock_bridge,
        patch(
            "compute.worker_cli.execute_work_unit_on_worker",
            side_effect=AssertionError("local execute should not run"),
        ),
    ):
        out = execute_claimed_work_unit(rec)
    mock_bridge.assert_called_once()
    assert out == broker


def test_worker_flag_on_broker_none_misses(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak431-d: COMPUTE=1 broker miss does not fall back to local execute."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    rec = _sample_rec()
    with (
        patch(
            "orchestrator.compute_broker_bridge.try_broker_compute_work",
            return_value=None,
        ),
        patch(
            "compute.worker_cli.execute_work_unit_on_worker",
            side_effect=AssertionError("local execute should not run"),
        ),
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            execute_claimed_work_unit(rec)


def test_normalize_compute_work_payload_wraps_mesh() -> None:
    from broker_client.stage_bind.compute import normalize_compute_work_payload

    mesh = {"run_id": "r1", "stage_name": "implementation", "payload": {"mesh": True}}
    out = normalize_compute_work_payload(mesh)
    assert out == {
        "action": "enqueue",
        "kind": "implementation",
        "payload": mesh,
    }
    already = {"action": "status", "job_id": "j1"}
    assert normalize_compute_work_payload(already) is already


def test_compute_action_builders() -> None:
    from broker_client.stage_bind.compute import (
        build_compute_claim_payload,
        build_compute_complete_payload,
        build_compute_enqueue_payload,
        build_compute_get_payload,
        normalize_compute_work_payload,
    )

    enq = build_compute_enqueue_payload("echo", {"n": 1})
    assert enq == {"action": "enqueue", "kind": "echo", "payload": {"n": 1}}
    claim = build_compute_claim_payload("node-1")
    assert claim == {"action": "claim", "node_id": "node-1"}
    done = build_compute_complete_payload(work_id="w1", node_id="node-1", result={"ok": True})
    assert done["action"] == "complete"
    assert done["result"] == {"ok": True}
    assert build_compute_get_payload("w1") == {"action": "get", "work_id": "w1"}
    assert normalize_compute_work_payload(claim) is claim


def test_worker_broker_payload_is_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    rec = _sample_rec()
    captured: list[dict] = []

    def _capture(payload: dict) -> dict:
        captured.append(payload)
        return {"ok": True, "via": "broker"}

    with (
        patch(
            "orchestrator.compute_broker_bridge.try_broker_compute_work",
            side_effect=_capture,
        ),
        patch(
            "compute.worker_cli.execute_work_unit_on_worker",
            side_effect=AssertionError("local execute should not run"),
        ),
    ):
        out = execute_claimed_work_unit(rec)
    assert out["via"] == "broker"
    assert captured[0]["action"] == "enqueue"
    assert captured[0]["kind"] == "implementation"
    assert captured[0]["payload"]["work_unit_id"] == str(rec.work_unit_id)


def test_pipeline_hook_broker_only_raise_no_local_fallback(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    sid = uuid4()
    run_id = uuid4()
    n1 = uuid4()
    with patch(
        "orchestrator.compute_broker_bridge.try_broker_compute_work",
        side_effect=RuntimeError("broker down"),
    ):
        with pytest.raises(RuntimeError, match="broker down"):
            mesh_assign_parallel_stages(
                run_id=run_id,
                stage_names=["implementation"],
                session_id=sid,
                workload_distribution="auto_share",
                node_ids=[n1],
                workspace=tmp_path,
            )
    with pytest.raises(RuntimeError, match=r"COMPUTE=1\|2"):
        get_work_unit_queue()


def test_pipeline_hook_broker_only_success_skips_local(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    sid = uuid4()
    run_id = uuid4()
    n1 = uuid4()
    with patch(
        "orchestrator.compute_broker_bridge.try_broker_compute_work",
        return_value={"work": {"id": "w-broker"}, "via": "broker"},
    ) as mock_bridge:
        mesh_assign_parallel_stages(
            run_id=run_id,
            stage_names=["implementation"],
            session_id=sid,
            workload_distribution="auto_share",
            node_ids=[n1],
            workspace=tmp_path,
        )
    mock_bridge.assert_called_once()
    with pytest.raises(RuntimeError, match=r"COMPUTE=1\|2"):
        get_work_unit_queue()


def test_worker_broker_only_raise_no_local_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    rec = _sample_rec()
    with (
        patch(
            "orchestrator.compute_broker_bridge.try_broker_compute_work",
            side_effect=RuntimeError("broker down"),
        ),
        patch(
            "compute.worker_cli.execute_work_unit_on_worker",
            side_effect=AssertionError("local execute should not run"),
        ),
    ):
        with pytest.raises(RuntimeError, match="broker down"):
            execute_claimed_work_unit(rec)


def test_worker_broker_only_success_skips_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    rec = _sample_rec()
    broker = {"ok": True, "via": "broker"}
    with (
        patch(
            "orchestrator.compute_broker_bridge.try_broker_compute_work",
            return_value=broker,
        ) as mock_bridge,
        patch(
            "compute.worker_cli.execute_work_unit_on_worker",
            side_effect=AssertionError("local execute should not run"),
        ),
    ):
        out = execute_claimed_work_unit(rec)
    mock_bridge.assert_called_once()
    assert out == broker


def test_mesh_host_sync_writer_miss_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak489-a: missing broker mesh unit raises instead of synthetic WriterStageResult."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    run_id = uuid4()
    with (
        patch(
            "broker_client.stage_bind.compute.compute_work_via_broker",
            return_value={"work": []},
        ),
        patch("compute.mesh_host_sync.mesh_wait_timeout_seconds", return_value=0.01),
        patch("compute.mesh_host_sync.mesh_poll_interval_seconds", return_value=0.0),
    ):
        from compute.mesh_host_sync import writer_stage_result_from_mesh

        with pytest.raises(RuntimeError, match="broker_miss"):
            writer_stage_result_from_mesh(run_id, "implementation")


def test_mesh_host_sync_critic_miss_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak489-a: critic_gate_fail_from_mesh raises on broker unit miss."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    run_id = uuid4()
    with (
        patch(
            "broker_client.stage_bind.compute.compute_work_via_broker",
            return_value={"work": []},
        ),
        patch("compute.mesh_host_sync.mesh_wait_timeout_seconds", return_value=0.01),
        patch("compute.mesh_host_sync.mesh_poll_interval_seconds", return_value=0.0),
    ):
        from compute.mesh_host_sync import critic_gate_fail_from_mesh

        with pytest.raises(RuntimeError, match="broker_miss"):
            critic_gate_fail_from_mesh(run_id, "security_critique")


def test_mesh_host_sync_list_transport_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak489-a: broker list transport failure propagates as broker_miss."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with patch(
        "broker_client.stage_bind.compute.compute_work_via_broker",
        side_effect=RuntimeError("transport down"),
    ):
        from compute.mesh_host_sync import _broker_list_units

        with pytest.raises(RuntimeError, match="transport down"):
            _broker_list_units(uuid4())


def test_mesh_host_sync_campaign_miss_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak491-g: campaign_slice_passed_from_mesh raises on broker unit miss."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    run_id = uuid4()
    slice_id = "slice-remote"
    with (
        patch(
            "broker_client.stage_bind.compute.compute_work_via_broker",
            return_value={"work": []},
        ),
        patch("compute.mesh_host_sync.mesh_wait_timeout_seconds", return_value=0.01),
        patch("compute.mesh_host_sync.mesh_poll_interval_seconds", return_value=0.0),
    ):
        from compute.mesh_host_sync import campaign_slice_passed_from_mesh

        with pytest.raises(RuntimeError, match="broker_miss"):
            campaign_slice_passed_from_mesh(run_id, slice_id)


def test_mesh_host_sync_campaign_list_transport_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak491-g: campaign_slice_passed_from_mesh propagates broker list transport miss."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    with patch(
        "broker_client.stage_bind.compute.compute_work_via_broker",
        side_effect=RuntimeError("transport down"),
    ):
        from compute.mesh_host_sync import campaign_slice_passed_from_mesh

        with pytest.raises(RuntimeError, match="transport down"):
            campaign_slice_passed_from_mesh(uuid4(), "slice-remote")


def test_absorb_completed_mesh_units_broker_miss_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak491-g: absorb raises on broker unit miss instead of silent skip."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    run_id = uuid4()
    store = MagicMock()
    with (
        patch(
            "broker_client.stage_bind.compute.compute_work_via_broker",
            return_value={"work": []},
        ),
        patch("compute.mesh_host_sync.mesh_wait_timeout_seconds", return_value=0.01),
        patch("compute.mesh_host_sync.mesh_poll_interval_seconds", return_value=0.0),
    ):
        from compute.mesh_host_sync import absorb_completed_mesh_units

        with pytest.raises(RuntimeError, match="broker_miss"):
            absorb_completed_mesh_units(store, run_id, ["implementation"])


def test_writers_parallel_refuses_local_under_compute_mesh(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sak489-b: local writer group refused when mesh expects broker dispatch."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from orchestrator.pipeline import make_dev_orchestrator

    orch, _store = make_dev_orchestrator()
    run_id = uuid4()
    sg: dict = {}
    session_id = uuid4()
    node_id = uuid4()
    with (
        patch(
            "orchestrator.collab.pipeline_hook.resolve_mesh_context_for_run",
            return_value=(session_id, "auto_share", [node_id]),
        ),
        patch(
            "orchestrator.role_claims_mesh.mesh_dispatch_context",
            return_value=({}, {}, None, None),
        ),
        patch(
            "orchestrator.collab.pipeline_hook.mesh_assign_parallel_stages",
            return_value={"implementation": None, "test_writer": None},
        ),
        patch(
            "orchestrator._pipeline.writers_parallel.asyncio.run",
            side_effect=AssertionError("local writers must not run"),
        ),
    ):
        with pytest.raises(RuntimeError, match="writers_parallel local runner"):
            orch._run_writers_parallel_dispatch(
                run_id,
                sg,
                ["implementation", "test_writer"],
                workspace=tmp_path,
            )


def test_probe_hardware_fixture_refuses_capacity(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak489-c: fixture/hw_fixture legacy probe blocked under CAPACITY peel."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from hw.probe import probe_hardware

    with pytest.raises(RuntimeError, match="hw_fixture"):
        monkeypatch.setenv("NIMBUSWARE_HW_FIXTURE", "weak")
        probe_hardware()

    with pytest.raises(RuntimeError, match="fixture unavailable"):
        monkeypatch.delenv("NIMBUSWARE_HW_FIXTURE", raising=False)
        probe_hardware(fixture="weak")


def test_pressure_limits_parallel_capacity_inline(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak489-c: pressure_limits_parallel avoids legacy import under CAPACITY peel."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "2")
    from hw.pressure import pressure_limits_parallel

    with patch("hw.pressure._legacy", side_effect=AssertionError("legacy must not run")):
        assert pressure_limits_parallel("block", 4) == 1
        assert pressure_limits_parallel("throttle", 4) == 2
        assert pressure_limits_parallel("ok", 4) == 4


def test_minimal_worker_ollama_miss_raises_under_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak489-c: Ollama sidecar miss raises under CAPACITY peel."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    with (
        patch(
            "broker_client.capacity_bridge.try_broker_probe_dict",
            return_value={
                "tier": "medium",
                "ram_total_gb": 16.0,
                "ram_available_gb": 8.0,
                "cpu_count": 4,
                "gpus": [],
                "gpu_groups": [],
                "unified_memory": False,
                "errors": [],
                "platform": "broker_capacity",
                "broker_capacity": True,
            },
        ),
        patch("httpx.get", side_effect=ConnectionError("ollama down")),
    ):
        from compute.minimal_worker import probe_minimal_worker_capabilities

        with pytest.raises(RuntimeError, match="ollama sidecar"):
            probe_minimal_worker_capabilities()


def test_broker_claim_empty_poll_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak490-a: empty claim is valid poll (not broker_miss)."""
    from compute.worker_cli import _broker_claim_execute_complete

    client = MagicMock()
    client.claim_work.return_value = {"work": None, "via": "broker"}
    with patch("broker_client.client.BrokerClient", return_value=client):
        assert _broker_claim_execute_complete("node-1") is False
    client.complete_work.assert_not_called()


def test_broker_claim_shape_miss_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak490-a: malformed work record is broker_miss (not empty poll)."""
    from compute.worker_cli import _broker_claim_execute_complete

    client = MagicMock()
    client.claim_work.return_value = {"work": {"kind": "mesh_stage"}, "via": "broker"}
    with patch("broker_client.client.BrokerClient", return_value=client):
        with pytest.raises(RuntimeError, match="broker_miss.*missing id"):
            _broker_claim_execute_complete("node-1")


def test_inmemory_queue_direct_ops_refuse_compute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak490-b: direct enqueue/dequeue/complete refuse under COMPUTE peel."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from compute.work_unit import InMemoryWorkUnitQueue

    queue = InMemoryWorkUnitQueue()
    run_id = uuid4()
    with pytest.raises(RuntimeError, match="broker_miss.*queue.enqueue"):
        queue.enqueue(run_id=run_id, stage_name="implementation")
    with pytest.raises(RuntimeError, match="broker_miss.*queue.dequeue"):
        queue.dequeue()
    with pytest.raises(RuntimeError, match="broker_miss.*queue.complete"):
        queue.complete(uuid4(), status="ok")


def test_inmemory_queue_read_ops_refuse_compute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak491-a: direct list_units/queued_count/terminate_restart refuse under COMPUTE peel."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from compute.work_unit import InMemoryWorkUnitQueue

    queue = InMemoryWorkUnitQueue()
    run_id = uuid4()
    with pytest.raises(RuntimeError, match="broker_miss.*queue.list_units"):
        queue.list_units(run_id=run_id)
    with pytest.raises(RuntimeError, match="broker_miss.*queue.queued_count"):
        queue.queued_count()
    with pytest.raises(RuntimeError, match="broker_miss.*queue.terminate_restart"):
        queue.terminate_restart(uuid4())


def test_readiness_memory_import_refuses_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak490-c: readiness memory ImportError does not weak-tier fallback under peel."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from maker.readiness.platform import _check_memory

    with patch("hw.cache.get_cached_profile", side_effect=ImportError("no hw")):
        with pytest.raises(RuntimeError, match="broker_miss.*memory import"):
            _check_memory()


def test_models_ranked_capacity_2_raises_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak490-d: models/ranked miss under CAPACITY=2 → HTTP 503 problem()."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "2")
    from unittest.mock import MagicMock

    from fastapi import HTTPException

    from api.routes import platform_model_routing as pmr

    orch = MagicMock()
    orch.repo_root = "."
    with patch(
        "api.routes.platform_model_routing.get_cached_profile",
        side_effect=RuntimeError("CAPACITY miss"),
    ):
        with pytest.raises(HTTPException) as ei:
            pmr.get_models_ranked(orch)
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_capacity_only"


def test_models_dependencies_capacity_2_raises_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak490-d: models/dependencies miss under CAPACITY=2 → HTTP 503 problem()."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "2")
    from unittest.mock import MagicMock

    from fastapi import HTTPException

    from api.routes import platform_model_routing as pmr

    orch = MagicMock()
    store = MagicMock()
    with patch(
        "api.routes.platform_model_routing.build_platform_readiness",
        side_effect=RuntimeError("memory import unavailable"),
    ):
        with pytest.raises(HTTPException) as ei:
            pmr.get_model_dependencies(orch, store)
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_capacity_only"
