from __future__ import annotations

from typing import Any
from uuid import UUID

from agent_core.models import EventType
from maker.approval import (
    STAGE_SLICE_PENDING,
    STAGE_SLICE_SKIPPED,
    STAGE_WORKSPACE_REVERTED,
    last_revert_snapshot_from_rows,
    pending_slice_from_rows,
)
from maker.slice_workflow._shared import emit_maker_stage
from maker.workspace.snapshot import restore_workspace_snapshot
from maker.workspace.workspace import resolve_run_workspace


def skip_pending_slice(orch: Any, run_id: UUID, slice_id: str) -> dict[str, Any]:
    rows = orch._store.list_run_events(str(run_id))
    pending = pending_slice_from_rows(rows)
    if pending is None:
        raise ValueError("no pending slice awaiting approval")
    if str(pending.get("slice_id")) != slice_id:
        raise ValueError(f"pending slice is {pending.get('slice_id')!r}, not {slice_id!r}")

    resolved = dict(pending)
    resolved["awaiting_approval"] = False
    emit_maker_stage(orch, run_id, STAGE_SLICE_PENDING, resolved)
    emit_maker_stage(orch, run_id, STAGE_SLICE_SKIPPED, {"slice_id": slice_id})
    return {"status": "skipped", "slice_id": slice_id}


def revert_workspace(orch: Any, run_id: UUID) -> dict[str, Any]:
    rows = orch._store.list_run_events(str(run_id))
    snapshot = last_revert_snapshot_from_rows(rows)
    if snapshot is None:
        raise ValueError("no approved workspace snapshot to revert to")
    ws = resolve_run_workspace(rows)
    restored = restore_workspace_snapshot(ws, snapshot)
    snap_paths = set(snapshot.get("paths") or [])
    for row in rows:
        if row.get("event_type") != EventType.STITCH_APPLIED.value:
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        for rel in payload.get("files_added") or []:
            rel_s = str(rel).replace("\\", "/").lstrip("/")
            if not rel_s or rel_s in snap_paths:
                continue
            target = ws / rel_s
            if target.is_file():
                target.unlink()
    emit_maker_stage(
        orch,
        run_id,
        STAGE_WORKSPACE_REVERTED,
        {
            "workspace_snapshot": snapshot,
            "paths_restored": restored,
        },
    )
    return {
        "status": "reverted",
        "snapshot_id": snapshot.get("snapshot_id"),
        "paths_restored": restored,
    }
