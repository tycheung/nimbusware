"""Product edition gate — Individual (default) vs Enterprise."""

from __future__ import annotations

import os
from typing import Any

ENV_EDITION = "NIMBUSWARE_EDITION"
DEFAULT_EDITION = "individual"
ENTERPRISE_EDITION = "enterprise"
VALID_EDITIONS = frozenset({DEFAULT_EDITION, ENTERPRISE_EDITION})

# Enterprise feature flags — enabled only when ``is_enterprise``.
ENTERPRISE_FEATURES: frozenset[str] = frozenset(
    {
        "iam",
        "fleet_memory",
        "config_notify",
        "object_store_primary",
        "redis_fleet_worker",
        "fleet_ollama_sli",
        "enterprise_console",
    },
)

_FEATURE_EPICS: dict[str, str] = {
    "iam": "fo201",
    "fleet_memory": "fo202",
    "config_notify": "fo203",
    "object_store_primary": "fo204",
    "redis_fleet_worker": "fo205",
    "fleet_ollama_sli": "fo206",
    "enterprise_console": "fo207",
}


class EnterpriseFeatureDisabledError(RuntimeError):
    """Raised when code paths require Enterprise edition."""


FEATURE_EPICS: dict[str, str] = _FEATURE_EPICS


def normalize_edition(raw: str | None, *, strict: bool = False) -> str:
    if raw is None or not str(raw).strip():
        return DEFAULT_EDITION
    value = str(raw).strip().lower()
    if value in VALID_EDITIONS:
        return value
    if strict:
        msg = f"invalid NIMBUSWARE_EDITION: {raw!r} (expected individual|enterprise)"
        raise ValueError(msg)
    return DEFAULT_EDITION


def edition() -> str:
    return normalize_edition(os.environ.get(ENV_EDITION))


def is_enterprise() -> bool:
    return edition() == ENTERPRISE_EDITION


def is_individual() -> bool:
    return not is_enterprise()


def enterprise_feature_enabled(feature: str) -> bool:
    """True when Enterprise edition is active and ``feature`` is a known enterprise flag."""
    return is_enterprise() and feature in ENTERPRISE_FEATURES


def require_enterprise_feature(feature: str) -> None:
    if not enterprise_feature_enabled(feature):
        msg = f"Enterprise edition required for feature {feature!r} (set {ENV_EDITION}=enterprise)"
        raise EnterpriseFeatureDisabledError(msg)


def edition_manifest() -> dict[str, Any]:
    """JSON-safe snapshot for API / install diagnostics."""
    from nimbusware_iam.constants import IMPLEMENTED_ENTERPRISE_FEATURES

    ed = edition()
    features: dict[str, dict[str, str]] = {}
    for name in sorted(ENTERPRISE_FEATURES):
        if ed == DEFAULT_EDITION:
            status = "unavailable"
        elif name in IMPLEMENTED_ENTERPRISE_FEATURES:
            status = "enabled"
        else:
            status = "planned"
        features[name] = {
            "status": status,
            "epic": _FEATURE_EPICS.get(name, ""),
        }
    return {
        "edition": ed,
        "individual": is_individual(),
        "enterprise": is_enterprise(),
        "env_var": ENV_EDITION,
        "features": features,
    }


def enterprise_compose_profiles() -> list[str]:
    """Docker Compose profiles suggested for this edition."""
    if is_enterprise():
        return ["worker"]
    return []


def enterprise_install_hints() -> list[str]:
    """Post-install operator hints keyed to edition."""
    if is_individual():
        return [
            "Individual edition: repo-scoped Nimbusware memory is enabled.",
            "Enterprise-only capabilities (IAM, fleet memory) stay disabled.",
        ]
    return [
        "Enterprise edition: IAM, fleet memory, NOTIFY, object-store, Redis worker, Ollama SLI, and console enabled.",
        "Enterprise IAM: bootstrap via POST /v1/enterprise/iam/bootstrap.",
        "Console: sidebar tenant switcher + Enterprise fleet dashboard.",
        "Start optional worker stack: docker compose --profile fleet --profile worker up -d",
        "Poetry redis group installed when --with-redis (default for enterprise).",
    ]
