from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.admin import AdminDep
from api.errors import problem
from api.schemas.peel_responses import long_tail_json_openapi_responses, with_long_tail_peel_503
from env.settings_catalog import SettingScope
from env.settings_resolve import catalog_payload_for_scope, refresh_scope_caches
from env.settings_store import (
    apply_all_managed_to_environ,
    get_scope_values,
    merge_scope_values,
)

router = APIRouter(tags=["platform"])


class SettingsPatchBody(BaseModel):
    values: dict[str, str] = Field(default_factory=dict, max_length=64)


class SettingsCatalogResponse(BaseModel):
    """GET /settings/catalog (`sak480-c`)."""

    install: dict[str, Any] = Field(default_factory=dict)
    system: dict[str, Any] = Field(default_factory=dict)
    user: dict[str, Any] = Field(default_factory=dict)
    run: dict[str, Any] = Field(default_factory=dict)
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class SettingsScopeResponse(BaseModel):
    """GET/PATCH settings scope payloads (`sak480-c`, `sak485-g`)."""

    model_config = {"extra": "allow"}

    groups: dict[str, Any] | None = None
    stored: dict[str, str] | None = None
    values: dict[str, str] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


def _mask_install_value(key: str, value: str | None) -> str | None:
    if value is None:
        return None
    secret_keys = frozenset(
        {
            "NIMBUSWARE_ADMIN_TOKEN",
            "NIMBUSWARE_API_KEY",
            "NIMBUSWARE_DATABASE_URL",
        },
    )
    if key in secret_keys and value:
        return "***"
    return value


@router.get(
    "/settings/catalog",
    response_model=SettingsCatalogResponse,
    response_model_exclude_none=True,
    summary="Settings catalog (`sak480-c`)",
    responses=long_tail_json_openapi_responses(),  # sak501-g
)
def get_settings_catalog() -> dict[str, Any]:
    return {
        "install": catalog_payload_for_scope(SettingScope.INSTALL),
        "system": catalog_payload_for_scope(SettingScope.SYSTEM),
        "user": catalog_payload_for_scope(SettingScope.USER),
        "run": catalog_payload_for_scope(SettingScope.RUN),
    }


@router.get(
    "/settings/install",
    response_model=SettingsScopeResponse,
    response_model_exclude_none=True,
    summary="Install settings (`sak480-c`)",
    responses=long_tail_json_openapi_responses(),  # sak501-g
)
def get_install_settings() -> dict[str, Any]:
    body = catalog_payload_for_scope(SettingScope.INSTALL)
    for defs in body.get("groups", {}).values():
        if not isinstance(defs, list):
            continue
        for item in defs:
            if isinstance(item, dict) and "key" in item:
                item["value"] = _mask_install_value(
                    str(item["key"]),
                    item.get("value") if isinstance(item.get("value"), str) else None,
                )
    return body


@router.get(
    "/settings/system",
    response_model=SettingsScopeResponse,
    response_model_exclude_none=True,
    summary="System settings (`sak480-c`)",
    responses=with_long_tail_peel_503(),  # sak518-a
)
def get_system_settings(_admin: AdminDep) -> dict[str, Any]:
    stored = get_scope_values(SettingScope.SYSTEM)
    payload = catalog_payload_for_scope(SettingScope.SYSTEM)
    for defs in payload.get("groups", {}).values():
        if not isinstance(defs, list):
            continue
        for item in defs:
            if isinstance(item, dict) and "key" in item:
                key = str(item["key"])
                if key in stored:
                    item["value"] = stored[key]
    payload["stored"] = stored
    return payload


@router.patch(
    "/settings/system",
    response_model=SettingsScopeResponse,
    summary="Patch system settings (`sak480-c`)",
    responses=with_long_tail_peel_503(),  # sak518-b
)
def patch_system_settings(body: SettingsPatchBody, _admin: AdminDep) -> dict[str, Any]:
    try:
        merged = merge_scope_values(SettingScope.SYSTEM, body.values, admin=True)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    apply_all_managed_to_environ()
    refresh_scope_caches()
    return {"values": merged}


@router.get(
    "/settings/me",
    response_model=SettingsScopeResponse,
    response_model_exclude_none=True,
    summary="User settings (`sak480-c`)",
    responses=with_long_tail_peel_503(),  # sak518-b
)
def get_user_settings() -> dict[str, Any]:
    stored = get_scope_values(SettingScope.USER)
    payload = catalog_payload_for_scope(SettingScope.USER)
    for defs in payload.get("groups", {}).values():
        if not isinstance(defs, list):
            continue
        for item in defs:
            if isinstance(item, dict) and "key" in item:
                key = str(item["key"])
                if key in stored:
                    item["value"] = stored[key]
    payload["stored"] = stored
    return payload


@router.patch(
    "/settings/me",
    response_model=SettingsScopeResponse,
    summary="Patch user settings (`sak480-c`)",
    responses=with_long_tail_peel_503(),  # sak518-c
)
def patch_user_settings(body: SettingsPatchBody) -> dict[str, Any]:
    try:
        merged = merge_scope_values(SettingScope.USER, body.values, admin=False)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    apply_all_managed_to_environ()
    refresh_scope_caches()
    return {"values": merged}
