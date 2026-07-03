from __future__ import annotations

from typing import Any

from env.env_flags import env_var_disable_flag_summary, env_var_tri_state_summary

__all__ = [
    "env_disable_flag_summary",
    "env_tri_state_summary",
]


def env_tri_state_summary(env_key: str) -> dict[str, Any]:
    return dict(env_var_tri_state_summary(env_key))


def env_disable_flag_summary(env_key: str, *, disable_key: str) -> dict[str, Any]:
    return dict(
        env_var_disable_flag_summary(env_key, disable_key=disable_key),
    )
