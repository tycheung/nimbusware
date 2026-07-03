from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.errors import problem
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


@router.post("/maker/push-subscriptions")
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


@router.delete("/maker/push-subscriptions")
def delete_push_subscription(endpoint: str = Query(..., min_length=8)) -> dict[str, Any]:
    if not push_web_enabled():
        raise HTTPException(
            status_code=503,
            detail=problem("push_not_configured", "Web Push is not configured"),
        )
    removed = unregister_push_subscription(endpoint)
    return {"endpoint": endpoint, "removed": removed}


@router.get("/maker/push-subscriptions")
def get_push_subscriptions() -> dict[str, Any]:
    if not push_web_enabled():
        return {"enabled": False, "vapid_public_key": None, "subscriptions": []}
    return {
        "enabled": True,
        "vapid_public_key": vapid_public_key(),
        "subscriptions": list_push_subscriptions(),
    }
