"""Enterprise config NOTIFY status."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from nimbusware_api.routes.enterprise import EnterpriseDep
from nimbusware_config import (
    NOTIFY_CHANNEL,
    NOTIFY_EVENT_TYPE,
    config_notify_enabled,
    config_notify_listener_enabled,
    get_config_notify_hub,
    listener_status,
)
from nimbusware_env.edition import enterprise_feature_enabled

router = APIRouter(prefix="/enterprise/config-notify", tags=["enterprise"])


@router.get("/status")
def config_notify_status(_gate: EnterpriseDep) -> dict[str, Any]:
    hub = get_config_notify_hub()
    return {
        "feature": "config_notify",
        "enabled": enterprise_feature_enabled("config_notify"),
        "listener_enabled": config_notify_listener_enabled(),
        "notify_flag": config_notify_enabled(),
        "channel": NOTIFY_CHANNEL,
        "event_type": NOTIFY_EVENT_TYPE,
        "hub": listener_status(hub),
    }
