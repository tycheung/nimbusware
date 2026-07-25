"""Thin mesh stage runner (`sak421-g` / `sak432-a`). Local body in ``mesh_stage_runner_legacy``."""

from __future__ import annotations

from typing import Any

from broker_client.flags import broker_compute_enabled
from compute.work_unit import WorkUnitRecord

_MSG = (
    "compute mesh_stage_runner local path unavailable under "
    "NIMBUSWARE_BROKER_COMPUTE=1|2; use SwissArmyNoife compute_work"
)


def _legacy():
    from compute import mesh_stage_runner_legacy as legacy

    return legacy


def execute_mesh_stage(*args: Any, **kwargs: Any) -> dict[str, Any]:
    if broker_compute_enabled():
        raise RuntimeError(_MSG)
    return _legacy().execute_mesh_stage(*args, **kwargs)


def execute_mesh_stage_on_worker(rec: WorkUnitRecord) -> dict[str, Any]:
    """Local mesh execute. Under ``NIMBUSWARE_BROKER_COMPUTE=1|2``, refuse local path (`sak488-i`)."""
    if broker_compute_enabled():  # sak488-i
        raise RuntimeError(_MSG)
    return _legacy().execute_mesh_stage_on_worker(rec)
