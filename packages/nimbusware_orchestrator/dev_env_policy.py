from __future__ import annotations

import os
from typing import Any

from agent_core.mapping import mapping_or_empty
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
    if not ce:
        return False
    profile = ce.get("workflow_profile") or ce.get("profile")
    if isinstance(profile, str) and profile in {
        "campaign_factory_zero_touch",
        "micro_slice_web",
        "factory_t3",
    }:
        return True
    return bool(mapping_or_empty(ce.get("persistent_dev_env")).get("enabled"))


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
    if not ce:
        return False
    if bool(mapping_or_empty(ce.get("ui_controller")).get("enabled")):
        return True
    if bool(mapping_or_empty(ce.get("persistent_dev_env")).get("ui_regression")):
        return True
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
    if not ce:
        return False
    if bool(mapping_or_empty(ce.get("launch_test")).get("enabled")):
        return True
    profile = ce.get("workflow_profile") or ce.get("profile")
    return isinstance(profile, str) and profile == "micro_slice_fullstack"
