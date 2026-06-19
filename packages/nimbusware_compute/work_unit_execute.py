from __future__ import annotations

from typing import Any

from nimbusware_compute.work_unit import WorkUnitRecord


def execute_work_unit_on_worker(rec: WorkUnitRecord) -> dict[str, Any]:
    """Bounded MVP executor: acknowledge mesh assignment locally on the claimer node."""
    return {
        "ok": True,
        "stage_name": rec.stage_name,
        "agent_role": rec.agent_role,
        "run_id": str(rec.run_id),
        "mesh_ack": True,
        "execute_on": "self",
    }
