"""Thin mesh host sync (`sak417-c` / `sak423-b` / `sak430-a` / `sak432-b` / `sak489-a` / `sak491-g`).

Legacy under ``=0``. Under ``COMPUTE=1|2``, poll SwissArmyNoife ``compute_work``
exclusively (no legacy fallback).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from uuid import UUID

from broker_client.flags import broker_compute_enabled
from orchestrator.parallel_writers import WriterStageResult

_MSG = (
    "compute mesh_host_sync local path unavailable under NIMBUSWARE_BROKER_COMPUTE=1|2; "
    "use SwissArmyNoife compute_work"
)

_TERMINAL_BROKER = frozenset({"completed", "failed"})
_TERMINAL_LOCAL = frozenset({"ok", "failed", "timeout", "cancelled"})


def _legacy():
    from compute import mesh_host_sync_legacy as legacy

    return legacy


def mesh_wait_timeout_seconds() -> float:
    return _legacy().mesh_wait_timeout_seconds()


def mesh_poll_interval_seconds() -> float:
    return _legacy().mesh_poll_interval_seconds()


def remote_stage_names(assignments: dict[str, UUID | None]) -> set[str]:
    if broker_compute_enabled():
        return {name for name, node_id in assignments.items() if node_id is not None}
    return _legacy().remote_stage_names(assignments)


def local_stage_names(assignments: dict[str, UUID | None]) -> set[str]:
    if broker_compute_enabled():
        return {name for name, node_id in assignments.items() if node_id is None}
    return _legacy().local_stage_names(assignments)


def _broker_list_units(run_id: UUID, stage_name: str | None = None) -> list[dict[str, Any]]:
    from broker_client.stage_bind.compute import (
        build_compute_list_payload,
        compute_work_via_broker,
    )
    from compute.broker_session_status import assert_broker_compute_ok

    payload = build_compute_list_payload(
        run_id=str(run_id),
        stage_name=stage_name,
        limit=200,
    )
    raw = assert_broker_compute_ok(
        compute_work_via_broker(payload),
        feature="mesh_host_sync.list",
        list_key="work",
    )
    work = raw.get("work")
    if isinstance(work, list):
        return [u for u in work if isinstance(u, dict)]
    if isinstance(work, dict):
        return [work]
    # sak441-a: assert_broker_compute_ok already requires list; keep defensive raise.
    raise RuntimeError("broker_miss: mesh_host_sync.list: work not a list")


def _unit_stage(unit: dict[str, Any]) -> str:
    kind = str(unit.get("kind") or "")
    payload = unit.get("payload") if isinstance(unit.get("payload"), dict) else {}
    return str(payload.get("stage_name") or kind or "")


def _unit_status(unit: dict[str, Any]) -> str:
    return str(unit.get("status") or "")


def _unit_result(unit: dict[str, Any]) -> dict[str, Any]:
    result = unit.get("result")
    return result if isinstance(result, dict) else {}


def _latest_broker_unit(
    units: list[dict[str, Any]],
    stage_name: str,
) -> dict[str, Any] | None:
    matches = [u for u in units if _unit_stage(u) == stage_name]
    if not matches:
        return None
    return matches[0]


def _require_mesh_unit(
    rec: dict[str, Any] | None,
    *,
    stage_name: str,
    feature: str,
) -> dict[str, Any]:
    """sak489-a: missing broker mesh unit is a hard miss under COMPUTE peel."""
    if rec is None:
        raise RuntimeError(
            f"broker_miss: mesh_host_sync.{feature}: no unit for stage {stage_name!r}"
        )
    return rec


def _broker_terminal(status: str) -> bool:
    return status in _TERMINAL_BROKER or status in _TERMINAL_LOCAL


def _wait_for_mesh_units_broker(
    run_id: UUID,
    stage_names: list[str],
    *,
    timeout_seconds: float | None = None,
) -> bool:
    if not stage_names:
        return True
    deadline = time.monotonic() + (timeout_seconds or mesh_wait_timeout_seconds())
    pending = set(stage_names)
    while pending and time.monotonic() < deadline:
        for stage in list(pending):
            units = _broker_list_units(run_id, stage)
            rec = _latest_broker_unit(units, stage)
            if rec is not None and _broker_terminal(_unit_status(rec)):
                pending.discard(stage)
        if pending:
            time.sleep(mesh_poll_interval_seconds())
    if pending:
        # sak489-a: timeout waiting for broker mesh units is not a silent False.
        raise RuntimeError(
            "broker_miss: mesh_host_sync.wait: stages not terminal: "
            f"{sorted(pending)!r}"
        )
    return True


def wait_for_mesh_units(
    run_id: UUID,
    stage_names: list[str],
    *,
    timeout_seconds: float | None = None,
) -> bool:
    # sak432-b: exclusive broker under COMPUTE=1|2 (no legacy fallback).
    if broker_compute_enabled():
        return _wait_for_mesh_units_broker(
            run_id, stage_names, timeout_seconds=timeout_seconds
        )
    return _legacy().wait_for_mesh_units(
        run_id, stage_names, timeout_seconds=timeout_seconds
    )


def critic_gate_fail_from_mesh(run_id: UUID, stage_name: str) -> bool:
    if broker_compute_enabled():
        units = _broker_list_units(run_id, stage_name)
        rec = _latest_broker_unit(units, stage_name)
        if rec is None or not _broker_terminal(_unit_status(rec)):
            wait_for_mesh_units(run_id, [stage_name])
            units = _broker_list_units(run_id, stage_name)
            rec = _latest_broker_unit(units, stage_name)
        rec = _require_mesh_unit(
            rec, stage_name=stage_name, feature="critic_gate_fail"
        )
        status = _unit_status(rec)
        if status not in {"completed", "ok"}:
            return True
        return bool(_unit_result(rec).get("gate_fail"))
    return _legacy().critic_gate_fail_from_mesh(run_id, stage_name)


def campaign_mesh_stage_name(slice_id: str) -> str:
    return f"campaign.slice:{slice_id}"


def campaign_slice_passed_from_mesh(run_id: UUID, slice_id: str) -> bool:
    # sak491-g: broker list/transport miss raises; no silent False under COMPUTE peel.
    if broker_compute_enabled():
        stage_name = campaign_mesh_stage_name(slice_id)
        units = _broker_list_units(run_id, stage_name)
        rec = _latest_broker_unit(units, stage_name)
        if rec is None or not _broker_terminal(_unit_status(rec)):
            wait_for_mesh_units(run_id, [stage_name])
            units = _broker_list_units(run_id, stage_name)
            rec = _latest_broker_unit(units, stage_name)
        rec = _require_mesh_unit(
            rec, stage_name=stage_name, feature="campaign_slice_passed"
        )
        if _unit_status(rec) not in {"completed", "ok"}:
            return False
        result = _unit_result(rec)
        if "slice_passed" in result:
            return bool(result.get("slice_passed"))
        return bool(result.get("executed", True))
    return _legacy().campaign_slice_passed_from_mesh(run_id, slice_id)


def writer_stage_result_from_mesh(run_id: UUID, stage_name: str) -> WriterStageResult:
    if broker_compute_enabled():
        units = _broker_list_units(run_id, stage_name)
        rec = _latest_broker_unit(units, stage_name)
        if rec is None or not _broker_terminal(_unit_status(rec)):
            wait_for_mesh_units(run_id, [stage_name])
            units = _broker_list_units(run_id, stage_name)
            rec = _latest_broker_unit(units, stage_name)
        rec = _require_mesh_unit(
            rec, stage_name=stage_name, feature="writer_stage_result"
        )
        status = _unit_status(rec)
        result = _unit_result(rec)
        if status in {"completed", "ok"}:
            return WriterStageResult(
                stage_name=stage_name,
                verifier_exit_code=int(result.get("verifier_exit_code") or 0),
                verifier_log=str(result.get("verifier_log") or "broker mesh ok"),
            )
        return WriterStageResult(
            stage_name=stage_name,
            verifier_exit_code=int(result.get("verifier_exit_code") or 1),
            verifier_log=str(
                result.get("verifier_log") or f"broker mesh status={status}"
            ),
        )
    return _legacy().writer_stage_result_from_mesh(run_id, stage_name)


def _absorb_completed_mesh_units_broker(
    store: Any,
    run_id: UUID,
    stage_names: list[str],
    *,
    host_workspace: Path | None = None,
) -> dict[str, int]:
    from compute.mesh_event_replay import replay_events_to_store_absorb
    from compute.mesh_workspace_merge import apply_workspace_files_absorb

    if not stage_names:
        return {"events_replayed": 0, "files_merged": 0}
    events_replayed = 0
    files_merged = 0
    for stage_name in stage_names:
        units = _broker_list_units(run_id, stage_name)
        rec = _latest_broker_unit(units, stage_name)
        if rec is None or not _broker_terminal(_unit_status(rec)):
            # sak491-g: no legacy silent skip under COMPUTE=1|2.
            wait_for_mesh_units(run_id, [stage_name])
            units = _broker_list_units(run_id, stage_name)
            rec = _latest_broker_unit(units, stage_name)
        rec = _require_mesh_unit(rec, stage_name=stage_name, feature="absorb")
        result = _unit_result(rec)
        replay_events = result.get("replay_events")
        if isinstance(replay_events, list):
            events_replayed += replay_events_to_store_absorb(store, run_id, replay_events)
        workspace_files = result.get("workspace_files")
        if host_workspace is not None and isinstance(workspace_files, dict) and workspace_files:
            files_merged += len(
                apply_workspace_files_absorb(
                    host_workspace,
                    {str(k): str(v) for k, v in workspace_files.items()},
                ),
            )
    return {"events_replayed": events_replayed, "files_merged": files_merged}


def absorb_completed_mesh_units(
    store: Any,
    run_id: UUID,
    stage_names: list[str],
    *,
    host_workspace: Path | None = None,
) -> dict[str, int]:
    if broker_compute_enabled():
        return _absorb_completed_mesh_units_broker(
            store, run_id, stage_names, host_workspace=host_workspace
        )
    return _legacy().absorb_completed_mesh_units(
        store, run_id, stage_names, host_workspace=host_workspace
    )
