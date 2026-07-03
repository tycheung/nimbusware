from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import yaml

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType, StagePassedEvent
from agent_core.models.events_payloads import StagePassedPayload
from env import find_repo_root

AUTOPILOT_UPDATED_STAGE = "run.autopilot.updated"

CHECKPOINT_CATALOG = (
    "stop_after_run_plan",
    "stop_after_slice_plan",
    "stop_before_workspace_apply",
    "stop_on_slice_test_fail",
    "stop_on_dev_env_regression_fail",
    "stop_on_ui_regression_fail",
    "stop_on_gate_fail",
    "stop_before_factory_complete",
    "stop_at_terminal_review",
    "stop_before_deploy_apply",
)


@dataclass
class AutopilotProfile:
    level: int
    name: str
    checkpoints: set[str] = field(default_factory=set)
    custom: bool = False

    def should_stop(self, checkpoint_id: str) -> bool:
        return checkpoint_id in self.checkpoints


def preset_for_level(level: int) -> AutopilotProfile:
    level = max(0, min(10, level))
    if level <= 2:
        checkpoints = set(CHECKPOINT_CATALOG)
    elif level <= 5:
        checkpoints = {
            "stop_on_dev_env_regression_fail",
            "stop_on_ui_regression_fail",
            "stop_on_gate_fail",
            "stop_before_factory_complete",
            "stop_at_terminal_review",
        }
    elif level <= 8:
        checkpoints = {
            "stop_on_gate_fail",
            "stop_before_factory_complete",
            "stop_at_terminal_review",
        }
    else:
        checkpoints = {"stop_at_terminal_review"}
    names = {
        0: "Full co-pilot",
        5: "Balanced",
        10: "Continuous improve",
    }
    name = names.get(level, f"Level {level}")
    return AutopilotProfile(level=level, name=name, checkpoints=checkpoints)


def default_autopilot_level_for_work_type(work_type: str | None) -> int:
    wt = str(work_type or "").strip().lower()
    if wt == "factory":
        return 10
    if wt == "patch":
        return 8
    return 5


def autopilot_effective_metadata(work_type: str | None) -> dict[str, Any]:
    level = default_autopilot_level_for_work_type(work_type)
    profile = preset_for_level(level)
    return {
        "level": profile.level,
        "name": profile.name,
        "checkpoints": sorted(profile.checkpoints),
        "source": "work_type_default",
    }


def presets_config_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "autopilot" / "presets.yaml"


def load_autopilot_presets(repo_root: Path | None = None) -> dict[str, Any]:
    path = presets_config_path(repo_root)
    if not path.is_file():
        return {"levels": {str(i): preset_for_level(i).checkpoints for i in range(11)}}
    return mapping_or_empty(yaml.safe_load(path.read_text(encoding="utf-8")))


def resolve_autopilot_profile(
    *,
    level: int | None = None,
    custom_checkpoints: set[str] | None = None,
) -> AutopilotProfile:
    if custom_checkpoints is not None:
        return AutopilotProfile(
            level=level or -1,
            name="Custom",
            checkpoints=set(custom_checkpoints),
            custom=True,
        )
    if level is not None:
        levels = mapping_or_empty(load_autopilot_presets()).get("levels")
        if isinstance(levels, dict):
            entry = mapping_or_empty(levels.get(str(level)))
            if entry and isinstance(entry.get("checkpoints"), list):
                return AutopilotProfile(
                    level=level,
                    name=str(entry.get("name") or preset_for_level(level).name),
                    checkpoints=set(str(c) for c in entry["checkpoints"]),
                )
    return preset_for_level(level if level is not None else 5)


_RUN_AUTOPILOT_OVERRIDES: dict[str, dict[str, Any]] = {}


def _autopilot_block_from_event_metadata(meta: dict[str, Any]) -> dict[str, Any] | None:
    block = mapping_or_empty(meta.get("autopilot"))
    return block or None


def _profile_from_autopilot_block(block: dict[str, Any]) -> AutopilotProfile:
    level_raw = block.get("level")
    level = int(level_raw) if level_raw is not None else 5
    checkpoints_raw = block.get("checkpoints")
    if isinstance(checkpoints_raw, list) and checkpoints_raw:
        return resolve_autopilot_profile(
            level=level,
            custom_checkpoints={str(c) for c in checkpoints_raw},
        )
    return resolve_autopilot_profile(level=level)


def persist_run_autopilot(
    store: Any,
    run_id: UUID | str,
    profile: AutopilotProfile,
    *,
    tenant_slug: str | None = None,
    repo_root: Path | None = None,
) -> AutopilotProfile:
    """Append durable autopilot override; also refresh in-process cache."""
    from orchestrator.fleet.policy_guards import enforce_tenant_autopilot_policy

    profile = enforce_tenant_autopilot_policy(
        profile,
        tenant_slug,
        repo_root=repo_root,
    )
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    block = {
        "level": profile.level,
        "name": profile.name,
        "checkpoints": sorted(profile.checkpoints),
        "custom": profile.custom,
    }
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            metadata={"autopilot": block},
            payload=StagePassedPayload(stage_name=AUTOPILOT_UPDATED_STAGE, duration_ms=0),
        ),
    )
    set_run_autopilot_override(
        str(rid),
        level=profile.level,
        checkpoints=set(profile.checkpoints) if profile.checkpoints else None,
    )
    return profile


def latest_autopilot_block_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in reversed(rows):
        pl = mapping_or_empty(row.get("payload"))
        if str(pl.get("stage_name") or "") != AUTOPILOT_UPDATED_STAGE:
            continue
        block = _autopilot_block_from_event_metadata(mapping_or_empty(row.get("metadata")))
        if block is not None:
            return block
    return None


def set_run_autopilot_override(
    run_id: str,
    *,
    level: int,
    checkpoints: set[str] | None = None,
) -> AutopilotProfile:
    profile = resolve_autopilot_profile(level=level, custom_checkpoints=checkpoints)
    _RUN_AUTOPILOT_OVERRIDES[str(run_id)] = {
        "level": profile.level,
        "checkpoints": sorted(profile.checkpoints),
        "name": profile.name,
        "custom": profile.custom,
    }
    return profile


def autopilot_level_from_rows(rows: list[dict[str, Any]]) -> int:
    persisted = latest_autopilot_block_from_rows(rows)
    if persisted is not None and persisted.get("level") is not None:
        return max(0, min(10, int(persisted["level"])))
    if rows:
        rid = str(rows[0].get("run_id", ""))
        override = mapping_or_empty(_RUN_AUTOPILOT_OVERRIDES.get(rid))
        if override.get("level") is not None:
            return max(0, min(10, int(override["level"])))
    meta = mapping_or_empty(_run_created_metadata(rows))
    if meta:
        for key in ("autopilot_effective", "autopilot"):
            block = mapping_or_empty(meta.get(key))
            if block.get("level") is not None:
                return max(0, min(10, int(block["level"])))
        if meta.get("autopilot_level") is not None:
            return max(0, min(10, int(meta["autopilot_level"])))
    return 5


def autopilot_profile_from_rows(rows: list[dict[str, Any]]) -> AutopilotProfile:
    persisted = latest_autopilot_block_from_rows(rows)
    if persisted is not None:
        return _profile_from_autopilot_block(persisted)
    if rows:
        rid = str(rows[0].get("run_id", ""))
        override = mapping_or_empty(_RUN_AUTOPILOT_OVERRIDES.get(rid))
        if override:
            cps = override.get("checkpoints")
            if isinstance(cps, list) and cps:
                return resolve_autopilot_profile(
                    level=int(override.get("level", 5)),
                    custom_checkpoints={str(c) for c in cps},
                )
            if override.get("level") is not None:
                return resolve_autopilot_profile(level=int(override["level"]))
    level = autopilot_level_from_rows(rows)
    custom: set[str] | None = None
    meta = mapping_or_empty(_run_created_metadata(rows))
    if meta:
        for key in ("autopilot_effective", "autopilot"):
            block = mapping_or_empty(meta.get(key))
            cps = block.get("checkpoints")
            if isinstance(cps, list):
                custom = {str(c) for c in cps}
                break
    return resolve_autopilot_profile(level=level, custom_checkpoints=custom)


_SEVERITY_RANK = {
    "info": 0,
    "low": 1,
    "warn": 2,
    "warning": 2,
    "medium": 3,
    "high": 4,
    "error": 4,
    "block": 5,
    "blocker": 5,
    "critical": 5,
    "pass": 0,
    "success": 0,
}


@dataclass(frozen=True)
class TheaterVisibility:
    min_severity: str
    include_context_compaction: bool
    include_agent_tool_detail: bool


def theater_visibility_for_level(level: int) -> TheaterVisibility:
    if level <= 2:
        return TheaterVisibility("info", True, True)
    if level <= 8:
        return TheaterVisibility("warn", True, False)
    return TheaterVisibility("block", False, False)


def autopilot_theater_filter_active(rows: list[dict[str, Any]]) -> bool:
    if latest_autopilot_block_from_rows(rows) is not None:
        return True
    meta = mapping_or_empty(_run_created_metadata(rows))
    if meta:
        for key in ("autopilot_effective", "autopilot"):
            if mapping_or_empty(meta.get(key)).get("level") is not None:
                return True
        if meta.get("autopilot_level") is not None:
            return True
    return False


def _run_created_metadata(rows: list[dict[str, Any]]) -> dict[str, Any]:
    for row in rows:
        if row.get("event_type") != "run.created":
            continue
        return mapping_or_empty(row.get("metadata"))
    return {}


def filter_theater_messages_for_autopilot(
    messages: list[dict[str, Any]],
    *,
    level: int,
) -> list[dict[str, Any]]:
    vis = theater_visibility_for_level(level)
    floor = _SEVERITY_RANK.get(vis.min_severity, 0)
    out: list[dict[str, Any]] = []
    for msg in messages:
        sev = str(msg.get("severity") or "info").lower()
        if _SEVERITY_RANK.get(sev, 0) < floor:
            continue
        kind = str(msg.get("message_kind") or "")
        if not vis.include_context_compaction and kind == "context":
            if sev not in {"block", "error", "high", "blocker", "critical"}:
                continue
        if not vis.include_agent_tool_detail and kind == "agent_tool":
            continue
        out.append(msg)
    return out


def deliberation_rounds_for_level(level: int) -> int:
    if level <= 2:
        return 0
    if level <= 5:
        return 2
    if level <= 8:
        return 3
    return 6
