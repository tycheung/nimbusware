from __future__ import annotations

from broker_client.flags import broker_compute_enabled
from compute.mesh_stage_runner import execute_mesh_stage_on_worker
from compute.work_unit import WorkUnitRecord

_MSG = (
    "compute work_unit_execute local path unavailable under "
    "NIMBUSWARE_BROKER_COMPUTE=1|2; use SwissArmyNoife compute_work"
)


def execute_work_unit_on_worker(rec: WorkUnitRecord) -> dict:
    """Execute a claimed mesh work unit on the worker node.

    Under ``NIMBUSWARE_BROKER_COMPUTE=1|2``, refuse local execute (`sak432-a`).
    Callers should claim/complete via broker (see ``worker_cli``).
    """
    if broker_compute_enabled():
        raise RuntimeError(_MSG)
    return execute_mesh_stage_on_worker(rec)
