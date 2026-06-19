from __future__ import annotations

from uuid import UUID

from nimbusware_compute.work_unit import WorkUnitRecord
from nimbusware_compute.work_unit_execute import execute_work_unit_on_worker


def test_execute_work_unit_on_worker_acknowledges_mesh() -> None:
    rec = WorkUnitRecord(
        work_unit_id=UUID("00000000-0000-4000-8000-000000000001"),
        run_id=UUID("00000000-0000-4000-8000-000000000002"),
        session_id=None,
        stage_name="slice.verify",
        agent_role="backend_writer",
        executor_user_id="",
        status="assigned",
        payload={"mesh_assignment": True},
    )
    out = execute_work_unit_on_worker(rec)
    assert out["ok"] is True
    assert out["stage_name"] == "slice.verify"
    assert out["mesh_ack"] is True
