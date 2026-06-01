"""Ollama model management API client (Admin Console)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from nimbusware_client.http import (
    admin_headers,
    delete_response,
    get_json,
    patch_response,
    post_json,
    user_headers,
)


def list_models(*, query: str = "") -> dict[str, Any]:
    path = "/platform/ollama/models"
    if query.strip():
        path = f"{path}?q={quote(query.strip())}"
    return get_json(path)


def save_user_policy(
    *,
    allow_pull: bool,
    allow_delete: bool,
    allow_update_routing: bool,
) -> dict[str, Any]:
    payload = {
        "allow_pull": allow_pull,
        "allow_delete": allow_delete,
        "allow_update_routing": allow_update_routing,
    }
    resp = patch_response(
        "/admin/ollama/user-policy",
        payload,
        headers={**user_headers(), **admin_headers()},
        timeout=30.0,
    )
    body = resp.json()
    return body if isinstance(body, dict) else payload


def admin_pull_model(model: str) -> dict[str, Any]:
    return post_json(
        "/admin/ollama/pull",
        {"model": model.strip()},
        headers={**user_headers(), **admin_headers()},
        timeout=600.0,
    )


def admin_delete_model(model_name: str) -> None:
    delete_response(
        f"/admin/ollama/models/{quote(model_name.strip(), safe='')}",
        headers={**user_headers(), **admin_headers()},
        timeout=120.0,
    )
