from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from api.deps import UserStoreDep
from api.routes.enterprise.core import EnterpriseDep
from api.schemas.peel_responses import enterprise_peel_json_openapi_responses

router = APIRouter(tags=["enterprise"])


class EnterpriseUserSearchResponse(BaseModel):
    """GET /users enterprise search (`sak486-e`)."""

    model_config = {"extra": "allow"}

    users: list[dict[str, Any]] = Field(default_factory=list)
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/users",
    response_model=EnterpriseUserSearchResponse,
    response_model_exclude_none=True,
    summary="Search enterprise users (`sak486-e`)",
    responses=enterprise_peel_json_openapi_responses(),  # sak496-e
)
def search_enterprise_users(
    _: EnterpriseDep,
    user_store: UserStoreDep,
    q: str = Query(default="", max_length=120),
) -> dict[str, Any]:
    rows = user_store.search_users(query=q, limit=20)
    return {
        "users": [
            {
                "user_id": str(u.user_id),
                "username": u.username,
                "display_name": u.display_name,
            }
            for u in rows
        ],
    }
