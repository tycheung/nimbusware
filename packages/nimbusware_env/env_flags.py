from __future__ import annotations

import os

TRUTHY_VALUES = frozenset({"1", "true", "yes"})
FALSY_VALUES = frozenset({"0", "false", "no"})


def env_str(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def env_bool(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    lowered = str(raw).strip().lower()
    if lowered in TRUTHY_VALUES:
        return True
    if lowered in FALSY_VALUES:
        return False
    return default


def env_truthy(name: str) -> bool:
    return env_str(name).lower() in TRUTHY_VALUES


def env_falsy(name: str) -> bool:
    return env_str(name).lower() in FALSY_VALUES


def hermes_slice_auto_advance_enabled() -> bool:
    raw = os.environ.get("HERMES_SLICE_AUTO_ADVANCE", "1").strip().lower()
    return raw not in FALSY_VALUES


def hermes_use_llm_enabled() -> bool:
    return env_truthy("HERMES_USE_LLM")


def hermes_skip_preflight_enabled() -> bool:
    return env_truthy("HERMES_SKIP_PREFLIGHT")


def env_tri_state(name: str) -> str | None:
    raw = env_str(name).lower()
    if raw in TRUTHY_VALUES:
        return "on"
    if raw in FALSY_VALUES:
        return "off"
    return None


def env_force_on(name: str) -> bool:
    return env_tri_state(name) == "on"


def env_force_off(name: str) -> bool:
    return env_tri_state(name) == "off"


def hermes_preflight_json_probe_enabled() -> bool:
    return env_truthy("HERMES_PREFLIGHT_JSON_PROBE")


def hermes_preflight_latency_sample_count(default: int = 1) -> int:
    raw = env_str("HERMES_PREFLIGHT_LATENCY_SAMPLES", str(default))
    try:
        n = int(raw)
    except ValueError:
        n = default
    return min(max(n, 1), 20)
