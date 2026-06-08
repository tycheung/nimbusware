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
    return preset_for_level(level if level is not None else 5)


def deliberation_rounds_for_level(level: int) -> int:
    if level <= 2:
        return 0
    if level <= 5:
        return 2
    if level <= 8:
        return 3
    return 6
