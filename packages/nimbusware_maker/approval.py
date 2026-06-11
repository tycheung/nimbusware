from __future__ import annotations

from typing import Any

from agent_core.models import EventType
from nimbusware_env.env_flags import nimbusware_slice_auto_advance_enabled

STAGE_PLAN_APPROVED = "slice.plan.approved"
STAGE_SLICE_PENDING = "slice.pending"
STAGE_SLICE_APPLIED = "slice.applied"
STAGE_SLICE_SKIPPED = "slice.skipped"
STAGE_WORKSPACE_SNAPSHOT = "workspace.snapshot.created"
STAGE_WORKSPACE_REVERTED = "workspace.reverted"


def slice_auto_advance_enabled(metadata: dict[str, Any] | None) -> bool:
    if not nimbusware_slice_auto_advance_enabled():
        return False
    if isinstance(metadata, dict):
        maker = metadata.get("maker_approval")
        if isinstance(maker, dict) and maker.get("enabled"):
            return False
    return True


def maker_approval_enabled_from_rows(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        if row.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = row.get("metadata")
        if isinstance(meta, dict):
            return not slice_auto_advance_enabled(meta)
    return False


def _stage_name(row: dict[str, Any]) -> str:
    payload = row.get("payload")
    if isinstance(payload, dict):
        name = payload.get("stage_name")
        if isinstance(name, str):
            return name.strip()
    return ""


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    meta = row.get("metadata")
    return dict(meta) if isinstance(meta, dict) else {}


def has_plan_approved(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        if row.get("event_type") == EventType.STAGE_PASSED.value:
            if _stage_name(row) == STAGE_PLAN_APPROVED:
                return True
    return False


def pending_slice_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    pending: dict[str, Any] | None = None
    for row in rows:
        if row.get("event_type") != EventType.STAGE_PASSED.value:
            continue
        if _stage_name(row) != STAGE_SLICE_PENDING:
            continue
        meta = _metadata(row)
        sid = str(meta.get("slice_id") or "").strip()
        if not sid:
            continue
        if not meta.get("awaiting_approval"):
            pending = None
            continue
        pending = {
            "slice_id": sid,
            "diff_unified": str(meta.get("diff_unified") or ""),
            "implement_mode": str(meta.get("implement_mode") or "scoped"),
            "rationale": str(meta.get("rationale") or ""),
            "target_paths": meta.get("target_paths")
            if isinstance(meta.get("target_paths"), list)
            else [],
            "proposed_edits": meta.get("proposed_edits"),
            "slice_plan": meta.get("slice_plan"),
            "slice_index": meta.get("slice_index"),
            "slice_total": meta.get("slice_total"),
        }
    return pending


def slice_is_resolved(rows: list[dict[str, Any]], slice_id: str) -> bool:
    for row in rows:
        if row.get("event_type") != EventType.STAGE_PASSED.value:
            continue
        meta = _metadata(row)
        if str(meta.get("slice_id") or "") != slice_id:
            continue
        stage = _stage_name(row)
        if stage in {STAGE_SLICE_APPLIED, STAGE_SLICE_SKIPPED}:
            return True
    return False


def last_revert_snapshot_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    from nimbusware_research.stitch_read_model import (
        stitch_applied_snapshot_from_events,
        stitch_events_present,
    )

    if stitch_events_present(rows):
        stitch_snap = stitch_applied_snapshot_from_events(rows)
        if stitch_snap is not None:
            return stitch_snap
    return last_approved_snapshot_from_rows(rows)


def git_outputs_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Branch / PR summary from slice.git_finalize stages."""
    out: dict[str, Any] = {}
    latest_seq = -1
    for row in rows:
        if row.get("event_type") != EventType.STAGE_PASSED.value:
            continue
        if _stage_name(row) != "slice.git_finalize":
            continue
        seq = int(row.get("store_seq") or 0)
        if seq < latest_seq:
            continue
        latest_seq = seq
        meta = _metadata(row)
        if meta.get("branch"):
            out["branch"] = str(meta["branch"])
        pr = meta.get("pr")
        if isinstance(pr, dict):
            if pr.get("pr_url"):
                out["pr_url"] = str(pr["pr_url"])
            out["pr_status"] = str(pr.get("status") or "")
    return out


def last_git_commit_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest per-slice git commit result from slice.applied maker stages."""
    latest: dict[str, Any] | None = None
    latest_seq = -1
    for row in rows:
        if row.get("event_type") != EventType.STAGE_PASSED.value:
            continue
        if _stage_name(row) != STAGE_SLICE_APPLIED:
            continue
        meta = _metadata(row)
        commit = meta.get("git_commit")
        if not isinstance(commit, dict):
            continue
        seq = int(row.get("store_seq") or 0)
        if seq >= latest_seq:
            latest_seq = seq
            latest = {**commit, "slice_id": meta.get("slice_id")}
    return latest


def last_approved_snapshot_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for row in rows:
        if row.get("event_type") != EventType.STAGE_PASSED.value:
            continue
        if _stage_name(row) not in {STAGE_SLICE_APPLIED, STAGE_WORKSPACE_SNAPSHOT}:
            continue
        snap = _metadata(row).get("workspace_snapshot")
        if isinstance(snap, dict) and snap.get("snapshot_id"):
            latest = dict(snap)
    return latest
