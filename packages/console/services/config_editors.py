from __future__ import annotations

from typing import Any

from client.http import admin_token_headers, delete_response, get_json, patch_response


def load_bundle_catalog(*, timeout: float = 10.0) -> dict[str, Any]:
    return get_json("/bundles/catalog", timeout=timeout)


def patch_bundle(
    bundle_id: str,
    payload: dict[str, Any],
    admin_token: str,
    *,
    timeout: float = 15.0,
) -> dict[str, Any]:
    resp = patch_response(
        f"/bundles/catalog/bundles/{bundle_id}",
        payload,
        headers=admin_token_headers(admin_token),
        timeout=timeout,
    )
    body = resp.json()
    return body if isinstance(body, dict) else {}


def load_persona_shelves(*, timeout: float = 10.0) -> dict[str, Any]:
    return get_json("/personas", timeout=timeout)


def patch_persona(
    persona_id: str,
    payload: dict[str, Any],
    admin_token: str,
    *,
    timeout: float = 15.0,
) -> None:
    patch_response(
        f"/personas/{persona_id}",
        payload,
        headers=admin_token_headers(admin_token),
        timeout=timeout,
    )


def delete_persona(persona_id: str, admin_token: str, *, timeout: float = 15.0) -> None:
    delete_response(
        f"/personas/{persona_id}",
        headers=admin_token_headers(admin_token),
        timeout=timeout,
    )
