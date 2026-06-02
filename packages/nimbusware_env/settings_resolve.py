"""Resolve operator settings: run → user → system → env → catalog default."""

from __future__ import annotations

import contextvars
import os
from typing import Any

from nimbusware_env.env_flags import FALSY_VALUES, TRUTHY_VALUES
from nimbusware_env.settings_catalog import CATALOG, SettingScope

_run_overrides: contextvars.ContextVar[dict[str, str] | None] = contextvars.ContextVar(
    "hermes_run_operator_settings",
    default=None,
)

_user_cache: dict[str, str] | None = None
_system_cache: dict[str, str] | None = None


def set_run_operator_settings(
    values: dict[str, str] | None,
) -> contextvars.Token[dict[str, str] | None]:
    return _run_overrides.set(values)


def reset_run_operator_settings(token: contextvars.Token[dict[str, str] | None]) -> None:
    _run_overrides.reset(token)


def operator_settings_from_run_metadata(metadata: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(metadata, dict):
        return {}
    raw = metadata.get("operator_settings")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key, val in raw.items():
        if key in CATALOG and val is not None:
            out[str(key)] = str(val).strip()
    return out


def refresh_scope_caches() -> None:
    global _user_cache, _system_cache
    try:
        from nimbusware_env.settings_store import get_scope_values

        _system_cache = get_scope_values(SettingScope.SYSTEM)
        _user_cache = get_scope_values(SettingScope.USER)
    except Exception:
        _system_cache = {}
        _user_cache = {}


def resolve_raw(key: str) -> str | None:
    if key not in CATALOG:
        env = os.environ.get(key)
        return str(env).strip() if env is not None and str(env).strip() else None
    defn = CATALOG[key]
    run = _run_overrides.get() or {}
    if key in run and run[key] != "":
        return run[key]
    if _user_cache is None or _system_cache is None:
        refresh_scope_caches()
    if defn.scope == SettingScope.USER and _user_cache and key in _user_cache:
        if _user_cache[key] != "":
            return _user_cache[key]
    if defn.scope == SettingScope.SYSTEM and _system_cache and key in _system_cache:
        if _system_cache[key] != "":
            return _system_cache[key]
    env = os.environ.get(key)
    if env is not None and str(env).strip() != "":
        return str(env).strip()
    return defn.default if defn.default != "" else None


def resolve_str(key: str, *, default: str = "") -> str:
    raw = resolve_raw(key)
    if raw is None:
        return default
    return raw


def resolve_bool(key: str, *, default: bool = False) -> bool:
    raw = resolve_raw(key)
    if raw is None or not str(raw).strip():
        return default
    lowered = str(raw).strip().lower()
    if lowered in TRUTHY_VALUES:
        return True
    if lowered in FALSY_VALUES:
        return False
    return default


def resolve_int(key: str, *, default: int) -> int:
    raw = resolve_raw(key)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default


def resolve_tri_state(key: str) -> str | None:
    raw = resolve_raw(key)
    if raw is None:
        return None
    lowered = str(raw).strip().lower()
    if lowered in TRUTHY_VALUES:
        return "on"
    if lowered in FALSY_VALUES:
        return "off"
    return None


def catalog_payload_for_scope(scope: SettingScope) -> dict[str, Any]:
    from nimbusware_env.settings_catalog import catalog_groups

    groups = catalog_groups(scope)
    values: dict[str, str | None] = {}
    for defs in groups.values():
        for d in defs:
            if scope == SettingScope.INSTALL:
                values[d.key] = os.environ.get(d.key, d.default) or None
            else:
                values[d.key] = resolve_raw(d.key)
    return {
        "scope": scope.value,
        "groups": {
            group: [
                {
                    "key": d.key,
                    "label": d.label,
                    "description": d.description,
                    "kind": d.kind.value,
                    "default": d.default,
                    "choices": list(d.choices),
                    "admin_editable": d.admin_editable,
                    "user_editable": d.user_editable,
                    "value": values.get(d.key),
                }
                for d in defs
            ]
            for group, defs in groups.items()
        },
    }
