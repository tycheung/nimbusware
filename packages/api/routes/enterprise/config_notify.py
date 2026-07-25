from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from api.routes.enterprise.core import EnterpriseDep
from api.schemas.peel_responses import enterprise_peel_json_openapi_responses
from config import (
    NOTIFY_CHANNEL,
    NOTIFY_EVENT_TYPE,
    config_notify_enabled,
    config_notify_listener_enabled,
    get_config_notify_hub,
    listener_status,
)
from env.edition import enterprise_feature_enabled

router = APIRouter(prefix="/enterprise/config-notify", tags=["enterprise"])


class ConfigNotifyStatusResponse(BaseModel):
    """GET /enterprise/config-notify/status (`sak486-e`)."""

    model_config = {"extra": "allow"}

    feature: str | None = None
    enabled: bool | None = None
    listener_enabled: bool | None = None
    notify_flag: bool | None = None
    channel: str | None = None
    event_type: str | None = None
    hub: dict[str, Any] | None = None
    via: str | None = None
    error: str | None = None


@router.get(
    "/status",
    response_model=ConfigNotifyStatusResponse,
    response_model_exclude_none=True,
    summary="Config notify status (`sak486-e`)",
    responses=enterprise_peel_json_openapi_responses(),  # sak496-e
)
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
