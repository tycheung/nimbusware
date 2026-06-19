from __future__ import annotations

import time
from uuid import UUID

from nimbusware_compute.work_unit import WorkUnitRecord, get_work_unit_queue
from nimbusware_env.env_flags import env_str
from nimbusware_orchestrator.parallel_writers import WriterStageResult

_TERMINAL = frozenset({"ok", "failed", "timeout", "cancelled"})


def _env_float(name: str, default: float) -> float:
    raw = env_str(name).strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def mesh_wait_timeout_seconds() -> float:
    return max(5.0, _env_float("NIMBUSWARE_MESH_WAIT_TIMEOUT_SECONDS", 300.0))


def mesh_poll_interval_seconds() -> float:
    return max(0.1, _env_float("NIMBUSWARE_MESH_POLL_INTERVAL_SECONDS", 0.5))


def remote_stage_names(assignments: dict[str, UUID | None]) -> set[str]:
    return {name for name, node_id in assignments.items() if node_id is not None}


def local_stage_names(assignments: dict[str, UUID | None]) -> set[str]:
    return {name for name, node_id in assignments.items() if node_id is None}


def _latest_unit(units: list[WorkUnitRecord], stage_name: str) -> WorkUnitRecord | None:
    matches = [u for u in units if u.stage_name == stage_name]
    if not matches:
        return None
    return sorted(matches, key=lambda u: u.created_at or u.work_unit_id.bytes)[-1]


def wait_for_mesh_units(
    run_id: UUID,
    stage_names: list[str],
    *,
    timeout_seconds: float | None = None,
) -> bool:
    if not stage_names:
        return True
    queue = get_work_unit_queue()
    deadline = time.monotonic() + (timeout_seconds or mesh_wait_timeout_seconds())
    pending = set(stage_names)
    while pending and time.monotonic() < deadline:
        units = queue.list_units(run_id=run_id)
        for stage in list(pending):
            rec = _latest_unit(units, stage)
            if rec is not None and rec.status in _TERMINAL:
                pending.discard(stage)
        if pending:
            time.sleep(mesh_poll_interval_seconds())
    return not pending


def critic_gate_fail_from_mesh(run_id: UUID, stage_name: str) -> bool:
    units = get_work_unit_queue().list_units(run_id=run_id)
    rec = _latest_unit(units, stage_name)
    if rec is None:
        return False
    if rec.status not in _TERMINAL:
        wait_for_mesh_units(run_id, [stage_name])
        rec = _latest_unit(get_work_unit_queue().list_units(run_id=run_id), stage_name)
    if rec is None:
        return True
    if rec.status != "ok":
        return True
    result = rec.result if isinstance(rec.result, dict) else {}
    return bool(result.get("gate_fail"))


def writer_stage_result_from_mesh(run_id: UUID, stage_name: str) -> WriterStageResult:
    units = get_work_unit_queue().list_units(run_id=run_id)
    rec = _latest_unit(units, stage_name)
    if rec is None:
        return WriterStageResult(
            stage_name=stage_name, verifier_exit_code=1, verifier_log="mesh unit missing"
        )
    if rec.status not in _TERMINAL:
        wait_for_mesh_units(run_id, [stage_name])
        rec = _latest_unit(get_work_unit_queue().list_units(run_id=run_id), stage_name)
    if rec is None:
        return WriterStageResult(
            stage_name=stage_name, verifier_exit_code=1, verifier_log="mesh unit missing"
        )
    result = rec.result if isinstance(rec.result, dict) else {}
    if rec.status != "ok":
        err = result.get("error") or rec.status
        return WriterStageResult(stage_name=stage_name, verifier_exit_code=1, verifier_log=str(err))
    if not result.get("executed", True):
        reason = result.get("reason") or "not_executed"
        return WriterStageResult(
            stage_name=stage_name, verifier_exit_code=1, verifier_log=str(reason)
        )
    exit_code = int(result.get("verifier_exit_code", 0))
    log = str(result.get("verifier_log") or result.get("status") or "remote_ok")
    return WriterStageResult(stage_name=stage_name, verifier_exit_code=exit_code, verifier_log=log)
