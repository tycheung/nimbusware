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
    if profile.custom:
        payload["custom"] = True
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


def apply_standards_at_run_start(
    store: Any,
    run_id: UUID | str,
    *,
    workspace: Path | None = None,
    repo_root: Path | None = None,
    user_profile_id: str | None = None,
    enforcement_level: int = 5,
) -> StandardsProfile | None:
    from standards.preset_defaults import workspace_standards_is_custom
    from standards.profile import resolve_standards_profile, standards_platform_enabled

    if not standards_platform_enabled():
        return None
    if workspace is None or not workspace.is_dir():
        return None
    if user_profile_id and str(user_profile_id).strip():
        profile = resolve_standards_profile(
            workspace=workspace,
            user_profile_id=str(user_profile_id).strip(),
            enforcement_level=enforcement_level,
            repo_root=repo_root,
        )
        return persist_run_standards(
            store,
            run_id,
            profile,
            workspace=workspace,
            write_overlay=True,
        )
    if workspace_standards_is_custom(workspace):
        profile = resolve_standards_profile(workspace=workspace, repo_root=repo_root)
        return persist_run_standards(
            store,
            run_id,
            profile,
            workspace=workspace,
            write_overlay=True,
        )
    profile = resolve_standards_profile(
        workspace=workspace,
        enforcement_level=enforcement_level,
        repo_root=repo_root,
    )
    return persist_run_standards(
        store,
        run_id,
        profile,
        workspace=workspace,
        write_overlay=False,
    )


def apply_standards_after_run_profiles(
    store: Any,
    run_id: UUID | str,
    *,
    workspace_path: str | None,
    repo_root: Path | None = None,
    standards_profile_id: str | None = None,
) -> StandardsProfile | None:
    from orchestrator.profiles.enforcement_profiles import enforcement_level_from_rows
    from standards.user_profiles import resolve_user_standards_profile

    if standards_profile_id and str(standards_profile_id).strip():
        if (
            resolve_user_standards_profile(
                str(standards_profile_id).strip(),
                repo_root=repo_root,
            )
            is None
        ):
            return None
    rows = store.list_run_events(str(run_id))
    level = enforcement_level_from_rows(rows) if rows else 5
    workspace = Path(workspace_path) if workspace_path and str(workspace_path).strip() else None
    return apply_standards_at_run_start(
        store,
        run_id,
        workspace=workspace,
        repo_root=repo_root,
        user_profile_id=standards_profile_id,
        enforcement_level=level,
    )


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
    repo_root: Path | None = None,
) -> StandardsProfile:
    from orchestrator.profiles.enforcement_profiles import enforcement_level_from_rows
    from standards.profile import resolve_standards_profile

    block = latest_standards_block_from_rows(rows)
    if block is None:
        level = enforcement_level_from_rows(rows) if rows else 5
        return resolve_standards_profile(
            workspace=workspace,
            enforcement_level=level,
            repo_root=repo_root,
        )
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
        custom=bool(block.get("custom", True)),
    )
