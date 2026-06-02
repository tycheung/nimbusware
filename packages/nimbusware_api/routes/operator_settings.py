"""Operator settings catalog and scoped PATCH endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nimbusware_api.admin import AdminDep
from nimbusware_api.errors import problem
from nimbusware_env.settings_catalog import SettingScope
from nimbusware_env.settings_resolve import catalog_payload_for_scope, refresh_scope_caches
from nimbusware_env.settings_store import (
    apply_all_managed_to_environ,
    get_scope_values,
    merge_scope_values,
)

router = APIRouter(tags=["platform"])


class SettingsPatchBody(BaseModel):
    values: dict[str, str] = Field(default_factory=dict, max_length=64)


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


@router.get("/settings/catalog")
def get_settings_catalog() -> dict[str, Any]:
    return {
        "install": catalog_payload_for_scope(SettingScope.INSTALL),
        "system": catalog_payload_for_scope(SettingScope.SYSTEM),
        "user": catalog_payload_for_scope(SettingScope.USER),
        "run": catalog_payload_for_scope(SettingScope.RUN),
    }


@router.get("/settings/install")
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


@router.get("/settings/system")
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


@router.patch("/settings/system")
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


@router.get("/settings/me")
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


@router.patch("/settings/me")
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
