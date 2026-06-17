from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from nimbusware_api.deps import UserStoreDep
from nimbusware_api.routes.enterprise.core import EnterpriseDep

router = APIRouter(tags=["enterprise"])


@router.get("/users")
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
