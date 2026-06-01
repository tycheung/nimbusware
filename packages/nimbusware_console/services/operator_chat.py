from __future__ import annotations

from typing import Any

from nimbusware_client.http import get_response, post_response, user_headers


def create_run(payload: dict[str, Any], *, timeout: float = 30.0):
    return post_response(
        "/runs",
        payload=payload,
        headers=user_headers(),
        timeout=timeout,
        raise_for_status=False,
    )


def fetch_timeline_response(run_id: str, *, timeout: float = 30.0):
    return get_response(
        f"/runs/{run_id}/timeline",
        headers=user_headers(),
        timeout=timeout,
        raise_for_status=False,
    )
