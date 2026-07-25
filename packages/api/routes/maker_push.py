from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.errors import problem
from api.schemas.peel_responses import long_tail_json_openapi_responses
from maker.push_subscriptions import (
    list_push_subscriptions,
    push_web_enabled,
    register_push_subscription,
    unregister_push_subscription,
    vapid_public_key,
)

router = APIRouter(tags=["maker"])


class PushSubscriptionBody(BaseModel):
    endpoint: str
    keys: dict[str, str] = Field(default_factory=dict)
    expirationTime: int | None = None
    run_id: str | None = None


class PushSubscriptionRegisterResponse(BaseModel):
    """POST /maker/push-subscriptions (`sak484-f`)."""

    model_config = {"extra": "allow"}

    endpoint: str | None = None
    registered: bool | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class PushSubscriptionDeleteResponse(BaseModel):
    """DELETE /maker/push-subscriptions (`sak484-f`)."""

    model_config = {"extra": "allow"}

    endpoint: str | None = None
    removed: bool | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class PushSubscriptionListResponse(BaseModel):
    """GET /maker/push-subscriptions (`sak484-f`)."""

    model_config = {"extra": "allow"}

    enabled: bool | None = None
    vapid_public_key: str | None = None
    subscriptions: list[dict[str, Any]] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.post(
    "/maker/push-subscriptions",
    response_model=PushSubscriptionRegisterResponse,
    response_model_exclude_none=True,
    summary="Register web-push subscription (`sak484-f`)",
    responses=long_tail_json_openapi_responses(),  # sak520-i
)
def post_push_subscription(body: PushSubscriptionBody) -> dict[str, Any]:
    if not push_web_enabled():
        raise HTTPException(
            status_code=503,
            detail=problem(
                "push_not_configured",
                "Web Push is not configured (set NIMBUSWARE_MAKER_VAPID_PUBLIC_KEY)",
            ),
        )
    payload = body.model_dump(exclude_none=True)
    run_id = payload.pop("run_id", None)
    return register_push_subscription(payload, run_id=run_id)


@router.delete(
    "/maker/push-subscriptions",
    response_model=PushSubscriptionDeleteResponse,
    response_model_exclude_none=True,
    summary="Unregister web-push subscription (`sak484-f`)",
    responses=long_tail_json_openapi_responses(),  # sak520-i
)
def delete_push_subscription(endpoint: str = Query(..., min_length=8)) -> dict[str, Any]:
    if not push_web_enabled():
        raise HTTPException(
            status_code=503,
            detail=problem("push_not_configured", "Web Push is not configured"),
        )
    removed = unregister_push_subscription(endpoint)
    return {"endpoint": endpoint, "removed": removed}


@router.get(
    "/maker/push-subscriptions",
    response_model=PushSubscriptionListResponse,
    response_model_exclude_none=True,
    summary="List web-push subscriptions (`sak484-f`)",
    responses=long_tail_json_openapi_responses(),  # sak501-i
)
def get_push_subscriptions() -> dict[str, Any]:
    if not push_web_enabled():
        return {"enabled": False, "vapid_public_key": None, "subscriptions": []}
    return {
        "enabled": True,
        "vapid_public_key": vapid_public_key(),
        "subscriptions": list_push_subscriptions(),
    }
