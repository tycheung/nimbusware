from __future__ import annotations

from typing import Any

from agent_core.mapping import mapping_or_empty
from agent_core.read.campaign import campaign_effective_from_rows
from env.env_flags import env_truthy
from orchestrator.micro_slice_run_context import run_created_metadata


def _dev_env_effective(rows: list[dict[str, Any]] | None) -> dict[str, Any]:
    if not rows:
        return {}
    return mapping_or_empty(run_created_metadata(rows).get("dev_env_effective"))


def persistent_dev_env_enabled(rows: list[dict[str, Any]] | None = None) -> bool:
    if env_truthy("NIMBUSWARE_DEV_ENV_ENABLED"):
        return True
    if not rows:
        return False
    if bool(_dev_env_effective(rows).get("enabled")):
        return True
    ce = campaign_effective_from_rows(rows)
    if not ce:
        return False
    profile = ce.get("workflow_profile") or ce.get("profile")
    if isinstance(profile, str) and profile in {
        "campaign_factory_zero_touch",
        "micro_slice_web",
        "micro_slice_fullstack",
        "factory_t3",
    }:
        return True
    return bool(mapping_or_empty(ce.get("persistent_dev_env")).get("enabled"))


def ui_controller_profile_enabled(rows: list[dict[str, Any]] | None = None) -> bool:
    if env_truthy("NIMBUSWARE_UI_CONTROLLER_ENABLED"):
        return True
    if not rows:
        return False
    de = _dev_env_effective(rows)
    if bool(de.get("ui_controller_enabled")):
        return True
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


def human_fidelity_profile_enabled(rows: list[dict[str, Any]] | None = None) -> bool:
    if env_truthy("NIMBUSWARE_HUMAN_FIDELITY_ENABLED"):
        return True
    return bool(_dev_env_effective(rows).get("human_fidelity_enabled"))


def launch_test_enabled(rows: list[dict[str, Any]] | None = None) -> bool:
    if env_truthy("NIMBUSWARE_LAUNCH_TEST_ENABLED"):
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
