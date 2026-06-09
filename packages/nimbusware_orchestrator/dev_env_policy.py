from __future__ import annotations

import os
from typing import Any

from agent_core.read.campaign import campaign_effective_from_rows


def persistent_dev_env_enabled(rows: list[dict[str, Any]] | None = None) -> bool:
    if os.environ.get("NIMBUSWARE_DEV_ENV_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
        return True
    if not rows:
        return False
    ce = campaign_effective_from_rows(rows)
    if not isinstance(ce, dict):
        return False
    profile = ce.get("workflow_profile") or ce.get("profile")
    if isinstance(profile, str) and profile in {
        "campaign_factory_zero_touch",
        "micro_slice_web",
        "factory_t3",
    }:
        return True
    block = ce.get("persistent_dev_env")
    if isinstance(block, dict):
        return bool(block.get("enabled"))
    return False


def ui_controller_profile_enabled(rows: list[dict[str, Any]] | None = None) -> bool:
    if os.environ.get("NIMBUSWARE_UI_CONTROLLER_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
        return True
    if not rows:
        return False
    ce = campaign_effective_from_rows(rows)
    if not isinstance(ce, dict):
        return False
    block = ce.get("ui_controller")
    if isinstance(block, dict):
        return bool(block.get("enabled"))
    ui_block = ce.get("persistent_dev_env")
    if isinstance(ui_block, dict):
        return bool(ui_block.get("ui_regression"))
    return persistent_dev_env_enabled(rows)


def ui_controller_enabled(rows: list[dict[str, Any]] | None = None) -> bool:
    return ui_controller_profile_enabled(rows)


def launch_test_enabled(rows: list[dict[str, Any]] | None = None) -> bool:
    if os.environ.get("NIMBUSWARE_LAUNCH_TEST_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
        return True
    if not rows:
        return False
    ce = campaign_effective_from_rows(rows)
    if not isinstance(ce, dict):
        return False
    block = ce.get("launch_test")
    if isinstance(block, dict):
        return bool(block.get("enabled"))
    profile = ce.get("workflow_profile") or ce.get("profile")
    return isinstance(profile, str) and profile == "micro_slice_fullstack"
