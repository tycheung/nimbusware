from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

from nimbusware_compute.mesh_stage_runner import execute_mesh_stage_on_worker
from nimbusware_compute.work_unit import WorkUnitRecord


def test_execute_mesh_stage_dispatches_writer_role(tmp_path: Path) -> None:
    rec = WorkUnitRecord(
        work_unit_id=UUID("00000000-0000-4000-8000-000000000001"),
        run_id=UUID("00000000-0000-4000-8000-000000000002"),
        session_id=None,
        stage_name="implementation",
        agent_role="implementation",
        executor_user_id="",
        status="assigned",
        payload={
            "mesh_assignment": True,
            "workspace": str(tmp_path),
            "taxonomy_key": "backend_writer",
        },
    )
    orch = MagicMock()
    with patch(
        "nimbusware_compute.mesh_stage_runner._mesh_orchestrator",
        return_value=orch,
    ):
        with patch(
            "nimbusware_compute.mesh_stage_runner.dispatch_role_execute",
            return_value={
                "status": "executed",
                "taxonomy_key": "backend_writer",
                "stage_name": "writers.verify",
                "run_id": str(rec.run_id),
            },
        ) as dispatch:
            out = execute_mesh_stage_on_worker(rec)
    dispatch.assert_called_once()
    assert out["ok"] is True
    assert out["executed"] is True
    assert out["mesh_ack"] is True
    assert out["taxonomy_key"] == "backend_writer"


def test_execute_mesh_stage_missing_workspace_mesh_acks() -> None:
    rec = WorkUnitRecord(
        work_unit_id=UUID("00000000-0000-4000-8000-000000000003"),
        run_id=UUID("00000000-0000-4000-8000-000000000004"),
        session_id=None,
        stage_name="security_critique",
        agent_role="security_critique",
        executor_user_id="",
        status="assigned",
        payload={"mesh_assignment": True},
    )
    out = execute_mesh_stage_on_worker(rec)
    assert out["ok"] is True
    assert out["mesh_ack"] is True
    assert out["executed"] is False
    assert out["reason"] == "missing_workspace"
