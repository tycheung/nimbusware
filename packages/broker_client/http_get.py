from __future__ import annotations

from typing import Any

import httpx

from broker_client.http import auth_headers


def get_json(
    base_url: str,
    path: str,
    *,
    token: str = "",
    timeout: float = 15.0,
    client: httpx.Client | None = None,
) -> Any:
    url = f"{base_url}{path}"
    headers = auth_headers(token)
    if client is not None:
        response = client.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()
    with httpx.Client(timeout=timeout) as owned:
        response = owned.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


def post_json(
    base_url: str,
    path: str,
    body: dict[str, Any],
    *,
    token: str = "",
    timeout: float = 15.0,
    client: httpx.Client | None = None,
) -> Any:
    """POST JSON to http-admin (`sak421-e/f`)."""
    url = f"{base_url}{path}"
    headers = {**auth_headers(token), "Content-Type": "application/json"}
    if client is not None:
        response = client.post(url, headers=headers, json=body, timeout=timeout)
        response.raise_for_status()
        return response.json()
    with httpx.Client(timeout=timeout) as owned:
        response = owned.post(url, headers=headers, json=body)
        response.raise_for_status()
        return response.json()
