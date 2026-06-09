"""Gradual dev-env activation milestones M1–M6 (§20.16)."""

from __future__ import annotations

import os
from typing import Any

from agent_core.models import EventType

MILESTONE_HTTP_REGRESSION = "M1"
MILESTONE_API_TESTS = "M2"
MILESTONE_NPM_DEV = "M3"
MILESTONE_CUSTOM_ADAPTER = "M4"
MILESTONE_MANUAL_START = "M5"
MILESTONE_UI_INTERACT = "M6"


def _milestone_ids_from_rows(rows: list[dict[str, Any]]) -> set[str]:
    achieved: set[str] = set()
    for row in rows:
        meta = row.get("metadata")
        if isinstance(meta, dict):
            block = meta.get("dev_env_milestone")
            if isinstance(block, dict):
                mid = str(block.get("id") or "").strip()
                if mid:
                    achieved.add(mid)
        et = str(row.get("event_type") or "")
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        stage = str(payload.get("stage_name") or "")
        if stage == "dev_env.started" and et == EventType.STAGE_STARTED.value:
            achieved.add(MILESTONE_MANUAL_START)
        if stage == "dev_env.regression" and et == EventType.STAGE_PASSED.value:
            achieved.add(MILESTONE_HTTP_REGRESSION)
        if stage == "slice.test" and et == EventType.STAGE_PASSED.value:
            achieved.add(MILESTONE_API_TESTS)
        if stage == "dev_env.ui_regression" and et == EventType.STAGE_PASSED.value:
            achieved.add(MILESTONE_UI_INTERACT)
    return achieved


def dev_env_milestones_achieved(rows: list[dict[str, Any]]) -> set[str]:
    if os.environ.get("NIMBUSWARE_DEV_ENV_MILESTONES_BYPASS", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
        return {
            MILESTONE_HTTP_REGRESSION,
            MILESTONE_API_TESTS,
            MILESTONE_NPM_DEV,
            MILESTONE_CUSTOM_ADAPTER,
            MILESTONE_MANUAL_START,
            MILESTONE_UI_INTERACT,
        }
    return _milestone_ids_from_rows(rows)


def dev_env_http_regression_enabled(rows: list[dict[str, Any]]) -> bool:
    from nimbusware_orchestrator.dev_env_policy import persistent_dev_env_enabled

    if not persistent_dev_env_enabled(rows):
        return False
    achieved = dev_env_milestones_achieved(rows)
    return MILESTONE_HTTP_REGRESSION in achieved or MILESTONE_MANUAL_START in achieved


def dev_env_auto_start_enabled(rows: list[dict[str, Any]]) -> bool:
    from nimbusware_orchestrator.dev_env_policy import persistent_dev_env_enabled

    if not persistent_dev_env_enabled(rows):
        return False
    if os.environ.get("NIMBUSWARE_DEV_ENV_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
        return True
    achieved = dev_env_milestones_achieved(rows)
    return (
        MILESTONE_HTTP_REGRESSION in achieved
        or MILESTONE_MANUAL_START in achieved
        or MILESTONE_API_TESTS in achieved
    )


def dev_env_ui_regression_enabled(rows: list[dict[str, Any]]) -> bool:
    from nimbusware_orchestrator.dev_env_policy import ui_controller_profile_enabled

    if not ui_controller_profile_enabled(rows):
        return False
    achieved = dev_env_milestones_achieved(rows)
    if MILESTONE_UI_INTERACT in achieved:
        return True
    # First UI regression attempt unlocks after HTTP regression milestone (M1/M5).
    return MILESTONE_HTTP_REGRESSION in achieved or MILESTONE_MANUAL_START in achieved
