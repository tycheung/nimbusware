"""HTTP client helpers for maker UI."""

from __future__ import annotations

import os
from typing import Any

import httpx


def api_base() -> str:
    return os.environ.get("NIMBUSWARE_API_BASE", "http://127.0.0.1:8000/v1").rstrip("/")


def admin_headers() -> dict[str, str]:
    token = os.environ.get("NIMBUSWARE_ADMIN_TOKEN", "").strip()
    if not token:
        return {}
    return {"X-Nimbusware-Admin-Token": token}


def get_json(path: str) -> dict[str, Any]:
    with httpx.Client(timeout=15.0) as client:
        r = client.get(f"{api_base()}{path}")
        r.raise_for_status()
        body = r.json()
        return body if isinstance(body, dict) else {"data": body}


def post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        r = client.post(f"{api_base()}{path}", json=payload, headers=admin_headers())
        r.raise_for_status()
        body = r.json()
        return body if isinstance(body, dict) else {"data": body}


def delete(path: str) -> None:
    with httpx.Client(timeout=15.0) as client:
        r = client.delete(f"{api_base()}{path}", headers=admin_headers())
        r.raise_for_status()
