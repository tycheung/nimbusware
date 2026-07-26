from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from compute.broker_session_status import (
    is_claim_empty_queue_error,
    normalize_claim_work_response,
)


def test_is_claim_empty_queue_error() -> None:
    assert is_claim_empty_queue_error({"work": None, "error": "queue empty"})
    assert is_claim_empty_queue_error({"work": None})
    assert not is_claim_empty_queue_error({"work": None, "error": "transport down"})
    assert not is_claim_empty_queue_error({"work": {"id": "w1"}})


def test_normalize_claim_empty_vs_miss() -> None:
    empty = normalize_claim_work_response({"work": None, "error": "no work available"})
    assert empty["work"] is None
    assert empty["via"] == "broker"
    with pytest.raises(RuntimeError, match="broker_miss"):
        normalize_claim_work_response({"work": None, "error": "broker unreachable"})
    # sak488-i: via=broker_miss must raise even when error mentions empty queue
    with pytest.raises(RuntimeError, match="broker_miss"):
        normalize_claim_work_response({"via": "broker_miss", "work": None, "error": "queue empty"})


def test_assert_list_via_broker_miss_with_empty_list() -> None:
    """sak488-i: peel miss with empty list is still a miss."""
    from compute.broker_session_status import assert_broker_compute_ok

    with pytest.raises(RuntimeError, match="broker_miss"):
        assert_broker_compute_ok(
            {"via": "broker_miss", "work": [], "status": "degraded"},
            feature="list_work_filtered",
            list_key="work",
        )
    out = assert_broker_compute_ok({"work": []}, feature="t", list_key="work")
    assert out["work"] == []


def test_mesh_stage_runner_refuses_under_compute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak488-i: local mesh execute refuses under COMPUTE=1|2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from compute.mesh_stage_runner import execute_mesh_stage_on_worker
    from compute.work_unit import WorkUnitRecord

    rec = WorkUnitRecord(
        work_unit_id=uuid4(),
        run_id=uuid4(),
        session_id=None,
        stage_name="mesh_stage",
        agent_role="",
        executor_user_id="u1",
        status="claimed",
        payload={},
    )
    with pytest.raises(RuntimeError, match="mesh_stage_runner local path unavailable"):
        execute_mesh_stage_on_worker(rec)


def test_worker_cli_execute_none_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from compute import worker_cli as wc

    client = MagicMock()
    client.claim_work.return_value = {
        "work": {"id": "w1", "kind": "mesh_stage", "payload": {}},
    }
    with (
        patch("broker_client.client.BrokerClient", return_value=client),
        patch("orchestrator.try_broker_compute_work", return_value=None),
    ):
        with pytest.raises(RuntimeError, match="execute returned None"):
            wc._broker_claim_execute_complete("n1")


def test_capacity_fit_error_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from broker_client.stage_bind import capacity as cap

    mcp = MagicMock()
    mcp.call_tool.return_value = {"error": "fit down"}
    with pytest.raises(RuntimeError, match="fit down"):
        cap.capacity_fit_via_broker([], binding_id="b1", client=mcp)


def test_redis_queue_refuses_under_compute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from compute.work_unit_redis import RedisWorkUnitQueue

    with pytest.raises(RuntimeError, match="RedisWorkUnitQueue unavailable"):
        RedisWorkUnitQueue("redis://localhost", client=MagicMock())


def test_terminate_restart_asserts_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    from broker_client.stage_bind.compute import terminate_restart_via_broker

    with patch(
        "broker_client.stage_bind.compute.compute_work_via_broker",
        return_value={"error": "requeue down", "work": None},
    ):
        with pytest.raises(RuntimeError, match="requeue down"):
            terminate_restart_via_broker("w1")
