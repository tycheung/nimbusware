"""Autopilot slider presets and custom checkpoint profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from nimbusware_env import find_repo_root

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


def presets_config_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "autopilot" / "presets.yaml"


def load_autopilot_presets(repo_root: Path | None = None) -> dict[str, Any]:
    path = presets_config_path(repo_root)
    if not path.is_file():
        return {"levels": {str(i): preset_for_level(i).checkpoints for i in range(11)}}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return raw if isinstance(raw, dict) else {}


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
        raw = load_autopilot_presets()
        levels = raw.get("levels") if isinstance(raw, dict) else None
        if isinstance(levels, dict):
            entry = levels.get(str(level))
            if isinstance(entry, dict) and isinstance(entry.get("checkpoints"), list):
                return AutopilotProfile(
                    level=level,
                    name=str(entry.get("name") or preset_for_level(level).name),
                    checkpoints=set(str(c) for c in entry["checkpoints"]),
                )
    return preset_for_level(level if level is not None else 5)


_RUN_AUTOPILOT_OVERRIDES: dict[str, dict[str, Any]] = {}


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
    if rows:
        rid = str(rows[0].get("run_id", ""))
        override = _RUN_AUTOPILOT_OVERRIDES.get(rid)
        if isinstance(override, dict) and override.get("level") is not None:
            return max(0, min(10, int(override["level"])))
    for row in rows:
        if row.get("event_type") != "run.created":
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            break
        for key in ("autopilot_effective", "autopilot"):
            block = meta.get(key)
            if isinstance(block, dict) and block.get("level") is not None:
                return max(0, min(10, int(block["level"])))
        if meta.get("autopilot_level") is not None:
            return max(0, min(10, int(meta["autopilot_level"])))
        break
    return 5


def autopilot_profile_from_rows(rows: list[dict[str, Any]]) -> AutopilotProfile:
    if rows:
        rid = str(rows[0].get("run_id", ""))
        override = _RUN_AUTOPILOT_OVERRIDES.get(rid)
        if isinstance(override, dict):
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
    for row in rows:
        if row.get("event_type") != "run.created":
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            break
        for key in ("autopilot_effective", "autopilot"):
            block = meta.get(key)
            if isinstance(block, dict) and isinstance(block.get("checkpoints"), list):
                custom = {str(c) for c in block["checkpoints"]}
                break
        break
    return resolve_autopilot_profile(level=level, custom_checkpoints=custom)


def deliberation_rounds_for_level(level: int) -> int:
    if level <= 2:
        return 0
    if level <= 5:
        return 2
    if level <= 8:
        return 3
    return 6
