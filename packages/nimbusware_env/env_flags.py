from __future__ import annotations

import os
import warnings
from pathlib import Path

from nimbusware_env.settings_catalog import CATALOG, SettingScope
from nimbusware_env.settings_resolve import (
    FAIL_CLOSED_RAW_KEYS,
    resolve_int,
    resolve_raw,
    resolve_str,
)

TRUTHY_VALUES = frozenset({"1", "true", "yes"})
FALSY_VALUES = frozenset({"0", "false", "no"})
_LEGACY_ENV_WARNED: set[str] = set()


def _warn_legacy_env_once(name: str, message: str) -> None:
    if name in _LEGACY_ENV_WARNED:
        return
    _LEGACY_ENV_WARNED.add(name)
    warnings.warn(message, DeprecationWarning, stacklevel=3)


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


_DEFAULT_OLLAMA_BASE = "http://127.0.0.1:11434"


def nimbusware_ollama_base_url(
    host: str | None = None,
    *,
    default: str = _DEFAULT_OLLAMA_BASE,
) -> str:
    if host:
        return host.rstrip("/")
    canonical = env_str("NIMBUSWARE_OLLAMA_BASE_URL")
    if canonical:
        return canonical.rstrip("/")
    legacy = os.environ.get("OLLAMA_HOST", "").strip()
    if legacy:
        _warn_legacy_env_once(
            "OLLAMA_HOST",
            "OLLAMA_HOST is deprecated; use NIMBUSWARE_OLLAMA_BASE_URL",
        )
        return legacy.rstrip("/")
    return default.rstrip("/")


def nimbusware_api_port(default: int = 8000) -> int:
    port_raw = env_str("NIMBUSWARE_API_PORT")
    if port_raw:
        try:
            return int(port_raw.strip())
        except ValueError:
            pass
    legacy = os.environ.get("PORT", "").strip()
    if legacy:
        try:
            _warn_legacy_env_once(
                "PORT",
                "PORT is deprecated for Nimbusware API bind; use NIMBUSWARE_API_PORT",
            )
            return int(legacy)
        except ValueError:
            pass
    return default


def nimbusware_api_base_url(*, default: str = "http://127.0.0.1:8000/v1") -> str:
    explicit = env_str("NIMBUSWARE_API_BASE")
    if explicit:
        return explicit.rstrip("/")
    host = nimbusware_api_host(default="127.0.0.1")
    if host in ("0.0.0.0", "::"):
        host = "127.0.0.1"
    return f"http://{host}:{nimbusware_api_port()}/v1"


def nimbusware_config_from_files_enabled() -> bool:
    return env_truthy("NIMBUSWARE_CONFIG_FROM_FILES")


def nimbusware_roles_from_db_enabled() -> bool:
    """Fail-closed: no strip (whitespace-padded values stay off)."""
    return env_truthy_raw("NIMBUSWARE_ROLES_FROM_DB")


def nimbusware_workflow_profile(default: str = "nimbusware_production") -> str:
    from nimbusware_env.settings_resolve import resolve_explicit_raw

    default_raw = resolve_explicit_raw("NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE")
    if default_raw:
        return default_raw
    legacy_raw = os.environ.get("NIMBUSWARE_WORKFLOW_PROFILE", "").strip()
    if legacy_raw:
        _warn_legacy_env_once(
            "NIMBUSWARE_WORKFLOW_PROFILE",
            "NIMBUSWARE_WORKFLOW_PROFILE is deprecated; use NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE",
        )
        return legacy_raw
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


def _context_max_chars_from_preset(preset_attr: str, fallback: int) -> int:
    from nimbusware_orchestrator.slice_budget_presets import resolve_slice_budget_preset

    return int(getattr(resolve_slice_budget_preset(), preset_attr))


def nimbusware_slice_packet_max_chars(default: int = 12000) -> int:
    return _context_max_chars_from_preset("packet_max_chars", default)


def nimbusware_slice_repo_map_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_SLICE_REPO_MAP_ENABLED", default=True)


def nimbusware_slice_repo_map_max_chars(default: int = 4000) -> int:
    return _context_max_chars_from_preset("repo_map_max_chars", default)


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
    return _context_max_chars_from_preset("symbol_sketch_max_chars", default)


def nimbusware_llm_history_max_chars(default: int = 2000) -> int:
    return _context_max_chars_from_preset("llm_history_max_chars", default)


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
    return _context_max_chars_from_preset("handoff_max_chars", default)


def nimbusware_memory_excerpt_max_chars(default: int = 4000) -> int:
    return _context_max_chars_from_preset("memory_excerpt_max_chars", default)


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
    if nimbusware_config_from_files_enabled():
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


def nimbusware_embed_dispatch_worker_enabled() -> bool:
    return env_bool("NIMBUSWARE_EMBED_DISPATCH_WORKER", default=False)


def nimbusware_integrator_probe_max_attempts(default: int = 3) -> int:
    return max(1, resolve_int("NIMBUSWARE_INTEGRATOR_PROBE_MAX_ATTEMPTS", default=default))


def nimbusware_integrator_probe_retry_delay(default: float = 0.25) -> float:
    raw = resolve_raw("NIMBUSWARE_INTEGRATOR_PROBE_RETRY_DELAY")
    if raw is None or not str(raw).strip():
        return default
    try:
        return max(0.0, float(str(raw).strip()))
    except ValueError:
        return default


def nimbusware_github_token() -> str | None:
    raw = env_str("GITHUB_TOKEN")
    return raw or None


def nimbusware_ci_github_repo() -> tuple[str, str] | None:
    raw = env_str("NIMBUSWARE_CI_GITHUB_REPO")
    if "/" not in raw:
        return None
    owner, repo = raw.split("/", 1)
    if not owner or not repo:
        return None
    return owner, repo


def nimbusware_gitlab_token() -> str | None:
    raw = env_str("NIMBUSWARE_GITLAB_TOKEN")
    if raw:
        return raw
    legacy = env_str("GITLAB_TOKEN")
    return legacy or None


def nimbusware_ci_gitlab_project() -> str | None:
    raw = env_str("NIMBUSWARE_CI_GITLAB_PROJECT")
    return raw or None


def nimbusware_gitlab_api_base() -> str:
    raw = env_str("NIMBUSWARE_GITLAB_API_BASE")
    return (raw or "https://gitlab.com/api/v4").rstrip("/")


def nimbusware_timeline_base_url(*, fallback: str = "") -> str:
    raw = env_str("NIMBUSWARE_TIMELINE_BASE_URL")
    return (raw or fallback).strip()


def nimbusware_ci_head_sha(*, default: str = "") -> str:
    return env_str("NIMBUSWARE_CI_HEAD_SHA") or default


def env_var_tri_state_summary(name: str) -> dict[str, object]:
    from nimbusware_env.settings_resolve import resolve_explicit_raw

    raw = resolve_explicit_raw(name) or ""
    low = raw.strip().lower()
    if not low:
        return {"raw": raw, "forces_off": False, "forces_on": False, "unset": True}
    if low in FALSY_VALUES:
        return {"raw": raw, "forces_off": True, "forces_on": False, "unset": False}
    if low in TRUTHY_VALUES:
        return {"raw": raw, "forces_off": False, "forces_on": True, "unset": False}
    return {
        "raw": raw,
        "forces_off": False,
        "forces_on": False,
        "unset": True,
        "unrecognised_value": True,
    }


def env_var_disable_flag_summary(name: str, *, disable_key: str) -> dict[str, object]:
    from nimbusware_env.settings_resolve import resolve_explicit_raw

    raw = resolve_explicit_raw(name) or ""
    low = raw.strip().lower()
    if not low:
        return {"raw": raw, disable_key: False, "unset": True}
    if low in FALSY_VALUES:
        return {"raw": raw, disable_key: True, "unset": False}
    return {
        "raw": raw,
        disable_key: False,
        "unset": False,
        "unrecognised_value": True,
    }


def env_over_yaml(key: str, yaml_value: bool) -> bool:
    from nimbusware_env.settings_resolve import env_over_yaml_resolved

    return env_over_yaml_resolved(key, yaml_value)


_DISPATCH_OFF = frozenset({"0", "false", "no", "off", "sync"})
_DISPATCH_MEMORY = frozenset({"memory", "1", "true", "yes", "on"})


def nimbusware_run_dispatch_mode() -> str | None:
    """Return ``memory``, ``redis``, or ``None`` when dispatch is disabled."""
    raw = env_str("NIMBUSWARE_RUN_DISPATCH").lower()
    if not raw or raw in _DISPATCH_OFF:
        return None
    if raw in _DISPATCH_MEMORY:
        return "memory"
    if raw == "redis":
        return "redis"
    return None


def nimbusware_redis_url() -> str:
    return env_str("NIMBUSWARE_REDIS_URL")


def nimbusware_repo_root_path(*, default: str = ".") -> Path:
    raw = env_str("NIMBUSWARE_REPO_ROOT", default=default) or default
    return Path(raw).resolve()


def nimbusware_database_url() -> str | None:
    url = env_str("NIMBUSWARE_DATABASE_URL")
    return url if url else None
