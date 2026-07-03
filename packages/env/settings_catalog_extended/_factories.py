from __future__ import annotations

from env.settings_catalog import (
    SettingDef,
    SettingKind,
    SettingScope,
)

_BOOL = SettingKind.BOOL
_INT = SettingKind.INT
_STR = SettingKind.STR
_ENUM = SettingKind.ENUM
_INSTALL = SettingScope.INSTALL
_SYSTEM = SettingScope.SYSTEM
_USER = SettingScope.USER
_INTERNAL = SettingScope.INTERNAL


def _uc(key: str, label: str) -> SettingDef:
    return SettingDef(
        key,
        _SYSTEM,
        _BOOL,
        "",
        label,
        "Empty = follow workflow YAML; set to force on/off.",
        "System — universal critique overrides",
    )


def _internal(
    key: str,
    label: str,
    *,
    kind: SettingKind = _STR,
    default: str = "",
    choices: tuple[str, ...] = (),
) -> SettingDef:
    return SettingDef(
        key,
        _INTERNAL,
        kind,
        default,
        label,
        "CI/dev/test only; not stored in Postgres.",
        "Internal — CI and dev",
        choices=choices,
        admin_editable=False,
        user_editable=False,
    )


def _install(
    key: str,
    label: str,
    *,
    kind: SettingKind = _STR,
    default: str = "",
    choices: tuple[str, ...] = (),
) -> SettingDef:
    return SettingDef(
        key,
        _INSTALL,
        kind,
        default,
        label,
        "Install / infrastructure (.env only).",
        "Install — infrastructure",
        choices=choices,
        admin_editable=False,
        user_editable=False,
    )
