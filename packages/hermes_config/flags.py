"""Feature flags for Postgres vs file-backed configuration."""

from __future__ import annotations

import os


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def config_from_db_enabled() -> bool:
    """True when operator config should load from Postgres (not repo YAML).

    Default on when ``HERMES_DATABASE_URL`` is set unless ``HERMES_CONFIG_FROM_FILES=1``.
  Explicit ``HERMES_CONFIG_FROM_DB=0`` / ``false`` / ``no`` disables even with a database URL.
    """
    if _truthy("HERMES_CONFIG_FROM_FILES"):
        return False
    if os.environ.get("HERMES_CONFIG_FROM_DB", "").strip().lower() in (
        "0",
        "false",
        "no",
    ):
        return False
    url = os.environ.get("HERMES_DATABASE_URL", "").strip()
    if url:
        return True
    return _truthy("HERMES_CONFIG_FROM_DB")
