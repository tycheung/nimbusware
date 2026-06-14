from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from nimbusware_env.settings_catalog import (
    CATALOG,
    KEY_SYSTEM,
    KEY_USER,
    NS_OPERATOR_SETTINGS,
    SettingDef,
    SettingKind,
    SettingScope,
)

if TYPE_CHECKING:
    from nimbusware_config.store import InMemoryConfigStore, PostgresConfigStore


def _conninfo() -> str | None:
    url = os.environ.get("NIMBUSWARE_DATABASE_URL", "").strip()
    return url or None


def _document_key(scope: SettingScope) -> str:
    if scope == SettingScope.SYSTEM:
        return KEY_SYSTEM
    if scope == SettingScope.USER:
        return KEY_USER
    msg = f"scope {scope} is not stored in config documents"
    raise ValueError(msg)


def _load_store() -> InMemoryConfigStore | PostgresConfigStore:
    from nimbusware_config.store import InMemoryConfigStore, PostgresConfigStore

    url = _conninfo()
    if url:
        return PostgresConfigStore(url)
    return InMemoryConfigStore()


def _values_from_content(content: dict[str, Any]) -> dict[str, str]:
    raw = content.get("values")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key, val in raw.items():
        if key in CATALOG and val is not None:
            out[str(key)] = str(val).strip()
    return out


def get_scope_values(scope: SettingScope) -> dict[str, str]:
    if scope not in (SettingScope.SYSTEM, SettingScope.USER):
        return {}
    store = _load_store()
    row = store.get(NS_OPERATOR_SETTINGS, _document_key(scope))
    if row is None:
        return {}
    return _values_from_content(row.content)


def validate_patch(
    patch: dict[str, str],
    *,
    scope: SettingScope,
    admin: bool,
) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for key, raw in patch.items():
        if key not in CATALOG:
            msg = f"unknown setting key: {key}"
            raise ValueError(msg)
        defn = CATALOG[key]
        if defn.scope != scope:
            msg = f"{key} is not in scope {scope.value}"
            raise ValueError(msg)
        if scope == SettingScope.SYSTEM and not admin and not defn.admin_editable:
            msg = f"{key} is not editable"
            raise ValueError(msg)
        if scope == SettingScope.USER and not defn.user_editable:
            msg = f"{key} is not user-editable"
            raise ValueError(msg)
        if scope == SettingScope.RUN and defn.scope != SettingScope.RUN:
            msg = f"{key} is not a run-scoped setting"
            raise ValueError(msg)
        cleaned[key] = _coerce(defn, str(raw))
    return cleaned


def _coerce(defn: SettingDef, raw: str) -> str:
    text = raw.strip()
    if defn.kind == SettingKind.BOOL:
        lowered = text.lower()
        if lowered in ("1", "true", "yes", "on"):
            return "1"
        if lowered in ("0", "false", "no", "off"):
            return "0"
        msg = f"{defn.key}: expected boolean (0/1)"
        raise ValueError(msg)
    if defn.kind == SettingKind.INT:
        if not text:
            return ""
        try:
            int(text)
        except ValueError as exc:
            msg = f"{defn.key}: expected integer"
            raise ValueError(msg) from exc
        return text
    if defn.kind == SettingKind.ENUM and defn.choices:
        if text not in defn.choices:
            msg = f"{defn.key}: must be one of {', '.join(defn.choices)}"
            raise ValueError(msg)
    return text


def merge_scope_values(
    scope: SettingScope,
    patch: dict[str, str],
    *,
    admin: bool = True,
) -> dict[str, str]:
    cleaned = validate_patch(patch, scope=scope, admin=admin)
    current = get_scope_values(scope)
    merged = {**current, **cleaned}
    store = _load_store()
    store.upsert(
        NS_OPERATOR_SETTINGS,
        _document_key(scope),
        {"values": merged},
    )
    return merged


def apply_scope_to_environ(scope: SettingScope) -> None:
    for key, val in get_scope_values(scope).items():
        if val != "":
            os.environ[key] = val


def apply_all_managed_to_environ() -> None:
    apply_scope_to_environ(SettingScope.SYSTEM)
    apply_scope_to_environ(SettingScope.USER)
