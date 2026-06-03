"""Read-only env summaries for Admin Console workflow explainers."""

from __future__ import annotations

from nimbusware_env.env_flags import env_str, env_tri_state
from nimbusware_env.settings_resolve import resolve_raw


def env_raw_summary(key: str) -> str:
    raw = resolve_raw(key)
    if raw is None or not str(raw).strip():
        return "unset"
    return str(raw)


def env_tri_state_summary(key: str) -> str:
    state = env_tri_state(key)
    if state is None:
        return "unset"
    return state


def env_bool_summary(key: str) -> str:
    raw = env_str(key)
    if not raw:
        return "unset"
    return raw
