"""Env flag helpers — prefer these over direct ``os.environ`` reads."""

from __future__ import annotations

import os

from nimbusware_env.settings_catalog import CATALOG, SettingScope
from nimbusware_env.settings_resolve import (
    FAIL_CLOSED_RAW_KEYS,
    resolve_int,
    resolve_raw,
    resolve_str,
)

TRUTHY_VALUES = frozenset({"1", "true", "yes"})
FALSY_VALUES = frozenset({"0", "false", "no"})


def _managed_key(name: str) -> bool:
    if name not in CATALOG:
        return False
    return CATALOG[name].scope not in (SettingScope.INSTALL, SettingScope.INTERNAL)


def env_str(name: str, default: str = "") -> str:
    if _managed_key(name):
        raw = resolve_raw(name)
        return raw if raw is not None else default
    return os.environ.get(name, default).strip()


def env_bool(name: str, *, default: bool = False) -> bool:
    raw = env_str(name) if _managed_key(name) else os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    lowered = str(raw).strip().lower()
    if lowered in TRUTHY_VALUES:
        return True
    if lowered in FALSY_VALUES:
        return False
    return default


def env_truthy(name: str) -> bool:
    if name in CATALOG and CATALOG[name].scope == SettingScope.INTERNAL:
        return os.environ.get(name, "").strip().lower() in TRUTHY_VALUES
    return env_str(name).lower() in TRUTHY_VALUES


def env_truthy_raw(name: str) -> bool:
    """Truthy check without stripping (fail-closed env contract)."""
    return os.environ.get(name, "").lower() in TRUTHY_VALUES


def env_falsy(name: str) -> bool:
    from nimbusware_env.settings_resolve import resolve_explicit_raw

    if name in CATALOG and CATALOG[name].scope == SettingScope.SYSTEM:
        raw = resolve_explicit_raw(name) or os.environ.get(name, "")
    else:
        raw = env_str(name) if _managed_key(name) else os.environ.get(name, "")
    return str(raw).strip().lower() in FALSY_VALUES


def nimbusware_slice_auto_advance_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_SLICE_AUTO_ADVANCE", default=True)


def nimbusware_use_llm_enabled() -> bool:
    """Fail-closed truthy tuple on raw env (no strip)."""
    return env_truthy_raw("NIMBUSWARE_USE_LLM")


def nimbusware_skip_preflight_enabled() -> bool:
    return env_truthy_raw("NIMBUSWARE_SKIP_PREFLIGHT")


def nimbusware_outbound_fetch_enabled() -> bool:
    return env_truthy_raw("NIMBUSWARE_OUTBOUND_FETCH_ENABLED")


def env_tri_state(name: str) -> str | None:
    from nimbusware_env.settings_resolve import resolve_tri_state

    if name in CATALOG and name not in FAIL_CLOSED_RAW_KEYS:
        return resolve_tri_state(name)
    raw = (
        os.environ.get(name, "").strip().lower()
        if name in FAIL_CLOSED_RAW_KEYS
        else env_str(name).lower()
    )
    if not raw:
        return None
    if raw in TRUTHY_VALUES:
        return "on"
    if raw in FALSY_VALUES:
        return "off"
    return None


def env_force_on(name: str) -> bool:
    return env_tri_state(name) == "on"


def env_force_off(name: str) -> bool:
    return env_tri_state(name) == "off"


def nimbusware_preflight_json_probe_enabled() -> bool:
    return env_truthy_raw("NIMBUSWARE_PREFLIGHT_JSON_PROBE")


def nimbusware_api_host(default: str = "0.0.0.0") -> str:
    raw = env_str("NIMBUSWARE_API_HOST")
    return raw or default


def nimbusware_workflow_profile(default: str = "nimbusware_production") -> str:
    from nimbusware_env.settings_resolve import resolve_explicit_raw

    for name in ("NIMBUSWARE_WORKFLOW_PROFILE", "NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE"):
        raw = resolve_explicit_raw(name)
        if raw:
            return raw
    return default


def nimbusware_preflight_latency_sample_count(default: int = 1) -> int:
    from nimbusware_env.settings_resolve import resolve_int as _ri

    return min(max(_ri("NIMBUSWARE_PREFLIGHT_LATENCY_SAMPLES", default=default), 1), 20)


def env_default_on(name: str, *, default: str = "1") -> bool:
    raw = env_str(name, default=default) if _managed_key(name) else os.environ.get(name, default)
    return str(raw).strip().lower() not in FALSY_VALUES


def nimbusware_run_bandit_enabled() -> bool:
    return env_truthy_raw("NIMBUSWARE_RUN_BANDIT")


def nimbusware_run_semgrep_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_RUN_SEMGREP", default=True)


def nimbusware_run_perf_scan_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_RUN_PERF_SCAN", default=True)


def nimbusware_run_mypy_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_RUN_MYPY", default=False)


def nimbusware_use_llm_explicitly_off() -> bool:
    raw = os.environ.get("NIMBUSWARE_USE_LLM")
    if raw is None or not str(raw).strip():
        return False
    return str(raw).strip().lower() in FALSY_VALUES


def nimbusware_slice_implement_mode() -> str:
    raw = resolve_str("NIMBUSWARE_SLICE_IMPLEMENT", default="scoped").lower()
    if raw in ("stub", "0", "false", "no"):
        return "stub"
    if raw == "agent":
        return "agent"
    if raw == "llm" or (raw in ("auto", "1", "true", "yes") and nimbusware_use_llm_enabled()):
        return "llm"
    return "scoped"


def nimbusware_research_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_RESEARCH", default=False)


def nimbusware_stitch_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_STITCH", default=False)


def nimbusware_git_native_outputs_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_GIT_NATIVE_OUTPUTS", default=False)


def nimbusware_git_pr_on_complete_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_GIT_PR_ON_COMPLETE", default=False)


def nimbusware_slice_auto_commit_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_SLICE_AUTO_COMMIT", default=False)


def nimbusware_slice_p3_evidence_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_SLICE_P3_EVIDENCE", default=True)


def nimbusware_slice_branch_prefix(default: str = "nimbusware/run-") -> str:
    return resolve_str("NIMBUSWARE_SLICE_BRANCH_PREFIX", default=default)


def nimbusware_slice_packet_max_chars(default: int = 12000) -> int:
    return resolve_int("NIMBUSWARE_SLICE_PACKET_MAX_CHARS", default=default)


def nimbusware_slice_repo_map_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_SLICE_REPO_MAP_ENABLED", default=True)


def nimbusware_slice_repo_map_max_chars(default: int = 4000) -> int:
    return resolve_int("NIMBUSWARE_SLICE_REPO_MAP_MAX_CHARS", default=default)


def nimbusware_slice_lsp_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_SLICE_LSP_ENABLED", default=True)


def nimbusware_slice_lsp_command() -> str | None:
    from nimbusware_env.settings_resolve import resolve_raw

    raw = resolve_raw("NIMBUSWARE_SLICE_LSP_COMMAND")
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def nimbusware_slice_lsp_timeout_sec(default: float = 8.0) -> float:
    from nimbusware_env.settings_resolve import resolve_raw

    raw = resolve_raw("NIMBUSWARE_SLICE_LSP_TIMEOUT_SEC")
    if raw is None or not str(raw).strip():
        return default
    try:
        return max(1.0, float(str(raw).strip()))
    except ValueError:
        return default


def nimbusware_slice_symbol_sketch_max_chars(default: int = 3000) -> int:
    return resolve_int("NIMBUSWARE_SLICE_SYMBOL_SKETCH_MAX_CHARS", default=default)


def nimbusware_llm_history_max_chars(default: int = 2000) -> int:
    return resolve_int("NIMBUSWARE_LLM_HISTORY_MAX_CHARS", default=default)


def nimbusware_read_max_chars(default: int = 16000) -> int:
    return resolve_int("NIMBUSWARE_READ_MAX_CHARS", default=default)


def nimbusware_shell_output_max_chars(default: int = 4000) -> int:
    return resolve_int("NIMBUSWARE_SHELL_OUTPUT_MAX_CHARS", default=default)


def nimbusware_agent_jit_loop_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_AGENT_JIT_LOOP", default=True)


def nimbusware_agent_compact_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_AGENT_COMPACT", default=True)


def nimbusware_projection_prune_agent_tools_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_PROJECTION_PRUNE_AGENT_TOOLS", default=True)


def nimbusware_agent_tools_list(
    default: str = "read,write,edit,grep,shell",
) -> tuple[str, ...]:
    raw = resolve_str("NIMBUSWARE_AGENT_TOOLS", default=default)
    parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    return tuple(parts) if parts else tuple(default.split(","))


def nimbusware_handoff_max_chars(default: int = 4000) -> int:
    return resolve_int("NIMBUSWARE_HANDOFF_MAX_CHARS", default=default)


def nimbusware_handoff_llm_summary_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_HANDOFF_LLM_SUMMARY", default=False)


def nimbusware_campaign_keep_recent_tokens(default: int = 12_000) -> int:
    raw = resolve_raw("NIMBUSWARE_CAMPAIGN_KEEP_RECENT_TOKENS")
    if raw is None or not str(raw).strip():
        return _campaign_tokens_from_hw(default)
    try:
        return max(1000, int(str(raw).strip()))
    except ValueError:
        return default


def nimbusware_campaign_reserve_tokens(default: int = 8000) -> int:
    return resolve_int("NIMBUSWARE_CAMPAIGN_RESERVE_TOKENS", default=default)


def _campaign_tokens_from_hw(default: int) -> int:
    try:
        from nimbusware_hw.cache import get_cached_profile

        profile = get_cached_profile()
        if profile is None:
            return default
        ctx = getattr(profile, "context_tokens", None) or getattr(profile, "context", None)
        if isinstance(ctx, int) and ctx > 2048:
            return max(4000, ctx // 3)
    except (ImportError, OSError, TypeError, ValueError):
        pass
    return default


def nimbusware_max_parallel_writers(default: int | None = None) -> int | None:
    raw = resolve_raw("NIMBUSWARE_MAX_PARALLEL_WRITERS")
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default


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


def env_over_yaml(key: str, yaml_value: bool) -> bool:
    from nimbusware_env.settings_resolve import env_over_yaml_resolved

    return env_over_yaml_resolved(key, yaml_value)
