from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def fetch_preflight_history(
    *,
    limit: int,
    order: str = "newest_first",
    include_metrics_export: bool = False,
    headers: Mapping[str, str] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    from nimbusware_client.http import get_response

    params: dict[str, str | int] = {
        "limit": max(1, min(50, int(limit))),
        "order": order,
    }
    if include_metrics_export:
        params["include_metrics_export"] = 1
    response = get_response(
        "/preflight-history",
        params=params,
        headers=dict(headers or {}),
        timeout=timeout,
    )
    body = response.json()
    return body if isinstance(body, dict) else {}
