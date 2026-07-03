from __future__ import annotations

from compute.mesh_stage_runner import execute_mesh_stage_on_worker
from compute.work_unit import WorkUnitRecord


def execute_work_unit_on_worker(rec: WorkUnitRecord) -> dict:
    """Execute a claimed mesh work unit on the worker node."""
    return execute_mesh_stage_on_worker(rec)
