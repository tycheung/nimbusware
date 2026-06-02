from __future__ import annotations

import os
from collections.abc import MutableMapping

QUICK_MODE_ENV = "NIMBUSWARE_QUICK_MODE"
DEFAULT_QUICK_WORKFLOW = "quick_local"


def quick_mode_enabled() -> bool:
    return os.environ.get(QUICK_MODE_ENV, "").strip().lower() in ("1", "true", "yes")


def _apply_quick(target: MutableMapping[str, str]) -> None:
    target[QUICK_MODE_ENV] = "1"
    target.pop("NIMBUSWARE_DATABASE_URL", None)
    target["HERMES_SKIP_PREFLIGHT"] = "1"
    target["NIMBUSWARE_CONFIG_FROM_FILES"] = "1"
    target.pop("NIMBUSWARE_CONFIG_FROM_DB", None)
    target.pop("NIMBUSWARE_ROLES_FROM_DB", None)
    target.setdefault("NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE", DEFAULT_QUICK_WORKFLOW)


def apply_quick_mode_env(env: dict[str, str] | None = None) -> dict[str, str]:
    """Configure in-memory API + stub slice workflow for solo local dev."""
    if env is None:
        _apply_quick(os.environ)
        return dict(os.environ)
    _apply_quick(env)
    return env
