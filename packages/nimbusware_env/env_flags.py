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


def env_truthy_raw(name: str) -> bool:
    """Truthy check without stripping — matches §14 fail-closed env contracts."""
    return os.environ.get(name, "").lower() in TRUTHY_VALUES


def env_falsy(name: str) -> bool:
    return env_str(name).lower() in FALSY_VALUES


def hermes_slice_auto_advance_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("HERMES_SLICE_AUTO_ADVANCE", default=True)


def hermes_use_llm_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("HERMES_USE_LLM", default=False)


def hermes_skip_preflight_enabled() -> bool:
    return env_truthy_raw("HERMES_SKIP_PREFLIGHT")


def hermes_outbound_fetch_enabled() -> bool:
    return env_truthy_raw("HERMES_OUTBOUND_FETCH_ENABLED")


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
    return env_truthy_raw("HERMES_PREFLIGHT_JSON_PROBE")


def nimbusware_api_host(default: str = "0.0.0.0") -> str:
    """HTTP bind host for ``nimbusware-api`` (Nimbusware platform)."""
    raw = env_str("NIMBUSWARE_API_HOST")
    if raw:
        return raw
    legacy = env_str("HERMES_API_HOST")
    return legacy or default


def nimbusware_workflow_profile(default: str = "nimbusware_production") -> str:
    """Default workflow profile for console display (Nimbusware platform)."""
    for name in ("NIMBUSWARE_WORKFLOW_PROFILE", "NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE"):
        raw = env_str(name)
        if raw:
            return raw
    legacy = env_str("HERMES_WORKFLOW_PROFILE")
    return legacy or default


def hermes_preflight_latency_sample_count(default: int = 1) -> int:
    raw = env_str("HERMES_PREFLIGHT_LATENCY_SAMPLES", str(default))
    try:
        n = int(raw)
    except ValueError:
        n = default
    return min(max(n, 1), 20)


def env_default_on(name: str, *, default: str = "1") -> bool:
    raw = os.environ.get(name, default).strip().lower()
    return raw not in FALSY_VALUES


def hermes_run_bandit_enabled() -> bool:
    return env_truthy_raw("HERMES_RUN_BANDIT")


def hermes_run_semgrep_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("HERMES_RUN_SEMGREP", default=True)


def hermes_run_perf_scan_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("HERMES_RUN_PERF_SCAN", default=True)


def hermes_use_llm_explicitly_off() -> bool:
    raw = os.environ.get("HERMES_USE_LLM")
    if raw is None or not str(raw).strip():
        return False
    return str(raw).strip().lower() in FALSY_VALUES


def hermes_slice_implement_mode() -> str:
    """``scoped`` (default), ``stub``, ``agent``, or ``llm``."""
    from nimbusware_env.settings_resolve import resolve_str

    raw = resolve_str("HERMES_SLICE_IMPLEMENT", default="scoped").lower()
    if raw in ("stub", "0", "false", "no"):
        return "stub"
    if raw == "agent":
        return "agent"
    if raw == "llm" or (raw in ("auto", "1", "true", "yes") and hermes_use_llm_enabled()):
        return "llm"
    return "scoped"


def nimbusware_config_from_db_enabled() -> bool:
    if env_truthy("NIMBUSWARE_CONFIG_FROM_FILES"):
        return False
    if env_str("NIMBUSWARE_CONFIG_FROM_DB").lower() in FALSY_VALUES:
        return False
    if env_str("NIMBUSWARE_DATABASE_URL"):
        return True
    return env_truthy("NIMBUSWARE_CONFIG_FROM_DB")


def nimbusware_config_notify_enabled() -> bool:
    if not env_truthy("NIMBUSWARE_CONFIG_NOTIFY"):
        return False
    try:
        from nimbusware_env.edition import enterprise_feature_enabled

        return enterprise_feature_enabled("config_notify")
    except ImportError:
        return False
