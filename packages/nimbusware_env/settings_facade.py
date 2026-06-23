from __future__ import annotations

from nimbusware_env import env_flags, settings_resolve

TRUTHY_VALUES = settings_resolve.TRUTHY_VALUES
FALSY_VALUES = settings_resolve.FALSY_VALUES

__all__ = [
    "env_bool",
    "env_str",
    "resolve_operator_setting",
]


def resolve_operator_setting(name: str) -> str | None:
    resolve_setting = getattr(settings_resolve, "resolve_setting", None)
    if resolve_setting is not None:
        return resolve_setting(name)
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
