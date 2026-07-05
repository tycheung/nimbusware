from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType, StagePassedEvent, StagePassedPayload
from standards.profile import StandardsProfile

STANDARDS_UPDATED_STAGE = "run.standards.updated"


def write_workspace_standards_overlay(workspace: Path, profile: StandardsProfile) -> None:
    import yaml

    overlay_dir = workspace / ".nimbusware"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {}
    if profile.facade_id:
        payload["facade_id"] = profile.facade_id
    if profile.bundle_ids:
        payload["bundles"] = list(profile.bundle_ids)
    if profile.connector_ids:
        payload["connectors"] = list(profile.connector_ids)
    if profile.verdict_overrides:
        payload["verdict_overrides"] = dict(profile.verdict_overrides)
    path = overlay_dir / "standards.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def persist_run_standards(
    store: Any,
    run_id: UUID | str,
    profile: StandardsProfile,
    *,
    workspace: Path | None = None,
    write_overlay: bool = True,
) -> StandardsProfile:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    if write_overlay and workspace is not None and workspace.is_dir():
        write_workspace_standards_overlay(workspace, profile)
    block = profile.to_dict()
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            metadata={"standards": block},
            payload=StagePassedPayload(stage_name=STANDARDS_UPDATED_STAGE, duration_ms=0),
        ),
    )
    return profile


def latest_standards_block_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in reversed(rows):
        pl = mapping_or_empty(row.get("payload"))
        if str(pl.get("stage_name") or "") != STANDARDS_UPDATED_STAGE:
            continue
        block = mapping_or_empty(mapping_or_empty(row.get("metadata")).get("standards"))
        if block:
            return block
    return None


def standards_profile_from_rows(
    rows: list[dict[str, Any]],
    *,
    workspace: Path | None = None,
) -> StandardsProfile:
    from standards.profile import resolve_standards_profile

    block = latest_standards_block_from_rows(rows)
    if block is None:
        return resolve_standards_profile(workspace=workspace)
    return StandardsProfile(
        profile_id=str(block.get("profile_id") or "default"),
        facade_id=str(block.get("facade_id") or "").strip() or None,
        bundle_ids=tuple(str(b) for b in block.get("bundle_ids") or []),
        connector_ids=tuple(str(c) for c in block.get("connector_ids") or []),
        stream_ids=tuple(str(s) for s in block.get("stream_ids") or []),
        verdict_overrides={
            str(k): v
            for k, v in (block.get("verdict_overrides") or {}).items()
            if v in ("skip", "warn", "critique", "hard_gate")
        },
    )
