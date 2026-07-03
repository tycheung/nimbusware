from __future__ import annotations

from env import env_flags
from env.settings_resolve import FALSY_VALUES, TRUTHY_VALUES, resolve_raw

__all__ = [
    "env_bool",
    "env_str",
    "resolve_operator_setting",
]


def resolve_operator_setting(name: str) -> str | None:
    catalog_val = resolve_raw(name)
    if catalog_val is not None:
        return catalog_val
    val = env_flags.env_str(name, default="")
    return val if val else None


def env_str(name: str, *, default: str = "") -> str:
    raw = resolve_operator_setting(name)
    if raw is not None:
        return raw
    return default


def env_bool(name: str, *, default: bool = False) -> bool:
    raw = resolve_operator_setting(name)
    if raw is None or not str(raw).strip():
        return default
    lowered = str(raw).strip().lower()
    if lowered in TRUTHY_VALUES:
        return True
    if lowered in FALSY_VALUES:
        return False
    return default
