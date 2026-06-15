from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _payload_load_error(payload: Mapping[str, Any] | None) -> bool:
    if not isinstance(payload, Mapping):
        return True
    load_error = payload.get("load_error")
    return isinstance(load_error, str) and bool(load_error.strip())


def _raw_detail(env: Mapping[str, Any]) -> str:
    raw = env.get("raw")
    if isinstance(raw, str) and raw.strip():
        return f" (raw={raw!r})"
    return ""


def env_tri_state_gate_caption(
    payload: Mapping[str, Any] | None,
    env_key: str,
    *,
    label: str,
    forces_off_text: str,
    forces_on_text: str,
    unset_text: str,
    unrecognised_text: str,
    unset_key: str = "unset",
) -> str | None:
    if _payload_load_error(payload):
        return None
    env = payload.get(env_key) if isinstance(payload, Mapping) else None
    if not isinstance(env, Mapping):
        return None
    detail = _raw_detail(env)
    if env.get("forces_off"):
        return forces_off_text.format(env_key=env_key, detail=detail)
    if env.get("forces_on"):
        return forces_on_text.format(env_key=env_key, detail=detail)
    if env.get(unset_key):
        return unset_text.format(env_key=env_key)
    if env.get("unrecognised_value"):
        return unrecognised_text.format(env_key=env_key, detail=detail)
    return None


def env_disable_flag_gate_caption(
    payload: Mapping[str, Any] | None,
    env_key: str,
    *,
    active_text: str,
    unset_text: str,
    unrecognised_text: str,
) -> str | None:
    if _payload_load_error(payload):
        return None
    env = payload.get(env_key) if isinstance(payload, Mapping) else None
    if not isinstance(env, Mapping):
        return None
    detail = _raw_detail(env)
    if (
        env.get("disables_feature")
        or env.get("disables_auto_promote")
        or env.get("disables_auto_create")
    ):
        return active_text.format(env_key=env_key, detail=detail)
    if env.get("unset"):
        return unset_text.format(env_key=env_key)
    if env.get("unrecognised_value"):
        return unrecognised_text.format(env_key=env_key, detail=detail)
    return None
