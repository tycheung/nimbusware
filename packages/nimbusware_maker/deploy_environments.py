from __future__ import annotations

from typing import Any

DEPLOY_ENVIRONMENTS: tuple[str, ...] = ("dev", "staging", "prod")
DEFAULT_DEPLOY_ENVIRONMENT = "dev"


def normalize_deploy_environment(value: str | None) -> str:
    raw = str(value or DEFAULT_DEPLOY_ENVIRONMENT).strip().lower()
    if raw not in DEPLOY_ENVIRONMENTS:
        raise ValueError(f"deploy_environment must be one of {', '.join(DEPLOY_ENVIRONMENTS)}")
    return raw


def deploy_environment_catalog() -> dict[str, Any]:
    return {
        "environments": list(DEPLOY_ENVIRONMENTS),
        "default": DEFAULT_DEPLOY_ENVIRONMENT,
    }


def resolve_deploy_environment(
    *,
    explicit: str | None = None,
    credentials: dict[str, Any] | None = None,
    manifest_raw: dict[str, Any] | None = None,
) -> str:
    if explicit:
        return normalize_deploy_environment(explicit)
    if isinstance(credentials, dict) and credentials.get("deploy_environment"):
        return normalize_deploy_environment(str(credentials["deploy_environment"]))
    if isinstance(manifest_raw, dict) and manifest_raw.get("deploy_environment"):
        return normalize_deploy_environment(str(manifest_raw["deploy_environment"]))
    return DEFAULT_DEPLOY_ENVIRONMENT
