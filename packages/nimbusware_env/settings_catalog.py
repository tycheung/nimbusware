from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SettingScope(str, Enum):
    INSTALL = "install"
    SYSTEM = "system"
    USER = "user"
    RUN = "run"
    INTERNAL = "internal"


class SettingKind(str, Enum):
    BOOL = "bool"
    INT = "int"
    STR = "str"
    ENUM = "enum"


@dataclass(frozen=True)
class SettingDef:
    key: str
    scope: SettingScope
    kind: SettingKind
    default: str
    label: str
    description: str
    group: str
    choices: tuple[str, ...] = ()
    admin_editable: bool = True
    user_editable: bool = True


NS_OPERATOR_SETTINGS = "operator_settings"
KEY_SYSTEM = "system"
KEY_USER = "user"


def _all_defs() -> tuple[SettingDef, ...]:
    from nimbusware_env.settings_catalog_extended import extended_defs

    return extended_defs()


CATALOG: dict[str, SettingDef] = {d.key: d for d in _all_defs()}


def catalog_for_scope(scope: SettingScope) -> list[SettingDef]:
    return [d for d in CATALOG.values() if d.scope == scope]


def catalog_groups(scope: SettingScope | None = None) -> dict[str, list[SettingDef]]:
    out: dict[str, list[SettingDef]] = {}
    for d in CATALOG.values():
        if scope is not None and d.scope != scope:
            continue
        out.setdefault(d.group, []).append(d)
    for items in out.values():
        items.sort(key=lambda x: x.key)
    return dict(sorted(out.items()))


def operator_catalog_defs() -> tuple[SettingDef, ...]:
    """User- and system-facing settings for Maker/Admin surfaces (excludes internal/run)."""
    return tuple(
        d
        for d in CATALOG.values()
        if d.scope in {SettingScope.USER, SettingScope.SYSTEM} and d.admin_editable
    )
