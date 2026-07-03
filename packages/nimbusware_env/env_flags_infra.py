from __future__ import annotations

from pathlib import Path

from nimbusware_env.env_flags import (
    env_bool,
    env_str,
    env_truthy_raw,
)
from nimbusware_env.settings_resolve import (
    FALSY_VALUES,
    TRUTHY_VALUES,
    resolve_explicit_raw,
    resolve_int,
    resolve_raw,
)


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


def _env_explicit_raw(name: str) -> tuple[str, str]:
    raw = resolve_explicit_raw(name) or ""
    return raw, raw.strip().lower()


def env_var_tri_state_summary(name: str) -> dict[str, object]:
    raw, low = _env_explicit_raw(name)
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
    raw, low = _env_explicit_raw(name)
    if not low:
        return {"raw": raw, disable_key: False, "unset": True}
    if low in FALSY_VALUES:
        return {"raw": raw, disable_key: True, "unset": False}
    return {"raw": raw, disable_key: False, "unset": False, "unrecognised_value": True}


def env_over_yaml(key: str, yaml_value: bool) -> bool:
    from nimbusware_env.settings_resolve import env_over_yaml_resolved

    return env_over_yaml_resolved(key, yaml_value)


_DISPATCH_OFF = frozenset({"0", "false", "no", "off", "sync"})
_DISPATCH_MEMORY = frozenset({"memory", "1", "true", "yes", "on"})


def nimbusware_verify_dispatch_fanout_enabled() -> bool:
    return env_truthy_raw("NIMBUSWARE_VERIFY_DISPATCH_FANOUT")


def nimbusware_run_dispatch_mode() -> str | None:
    raw = env_str("NIMBUSWARE_RUN_DISPATCH").lower()
    if not raw or raw in _DISPATCH_OFF:
        return None
    if raw in _DISPATCH_MEMORY:
        return "memory"
    if raw == "redis":
        return "redis"
    return None


def nimbusware_compute_work_queue_mode() -> str | None:
    raw = env_str("NIMBUSWARE_COMPUTE_WORK_QUEUE").lower()
    if not raw or raw in _DISPATCH_OFF:
        return None
    if raw in _DISPATCH_MEMORY:
        return "memory"
    if raw == "redis":
        return "redis"
    if raw == "postgres":
        return "postgres"
    return None


def nimbusware_redis_url() -> str:
    return env_str("NIMBUSWARE_REDIS_URL")


def nimbusware_repo_root_path(*, default: str = ".") -> Path:
    raw = env_str("NIMBUSWARE_REPO_ROOT", default=default) or default
    return Path(raw).resolve()


def nimbusware_database_url() -> str | None:
    url = env_str("NIMBUSWARE_DATABASE_URL")
    return url if url else None


def nimbusware_collab_enabled() -> bool:
    from nimbusware_env.collab_runtime import runtime_collab_override

    override = runtime_collab_override()
    if override is not None:
        return override
    return env_truthy_raw("NIMBUSWARE_COLLAB_ENABLED")


def nimbusware_workspace_path(*, default: str = "") -> Path:
    raw = env_str("NIMBUSWARE_WORKSPACE", default=default) or default
    if not raw:
        return Path(".").resolve()
    return Path(raw).resolve()


def nimbusware_api_key() -> str:
    return env_str("NIMBUSWARE_API_KEY")


def nimbusware_clone_url(
    default: str = "https://github.com/tycheung/nimbusware.git",
) -> str:
    raw = env_str("NIMBUSWARE_CLONE_URL", default=default).strip()
    return raw or default


def nimbusware_sandbox_backend(default: str = "none") -> str:
    return env_str("NIMBUSWARE_SANDBOX_BACKEND", default=default).strip().lower()


def nimbusware_sandbox_docker_image(default: str = "python:3.11-slim") -> str:
    raw = env_str("NIMBUSWARE_SANDBOX_DOCKER_IMAGE", default=default).strip()
    return raw or default


def nimbusware_tenant_id(default: str = "default") -> str:
    raw = env_str("NIMBUSWARE_TENANT_ID", default=default).strip()
    return raw or default


def nimbusware_bundle_memory_rank_weight(default: float = 0.2) -> float:
    raw = env_str("NIMBUSWARE_BUNDLE_MEMORY_RANK_WEIGHT", default=str(default)).strip()
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(0.0, min(1.0, value))


def nimbusware_memory_index_dir() -> str:
    return env_str("NIMBUSWARE_MEMORY_INDEX_DIR")


def nimbusware_workspace_snapshot_dir() -> str:
    return env_str("NIMBUSWARE_WORKSPACE_SNAPSHOT_DIR")


def nimbusware_scraper_artifact_max_age_days_raw() -> str:
    return env_str("NIMBUSWARE_SCRAPER_ARTIFACT_MAX_AGE_DAYS")


def nimbusware_fleet_memory_store_uri() -> str:
    return env_str("NIMBUSWARE_FLEET_MEMORY_STORE_URI")


def nimbusware_fleet_memory_store_dir() -> str:
    return env_str("NIMBUSWARE_FLEET_MEMORY_STORE_DIR")


def nimbusware_hw_fixture() -> str | None:
    raw = env_str("NIMBUSWARE_HW_FIXTURE")
    return raw if raw else None


def nimbusware_memory_embedding_model() -> str:
    return env_str("NIMBUSWARE_MEMORY_EMBEDDING_MODEL")


def env_truthy_on(name: str) -> bool:
    """Truthy check including ``on`` (scraper / legacy env contract)."""
    return env_str(name).lower() in (*TRUTHY_VALUES, "on")


def env_int_min(name: str, *, default: int, minimum: int = 1) -> int:
    return max(minimum, resolve_int(name, default=default))
