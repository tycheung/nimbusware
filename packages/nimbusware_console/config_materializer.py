"""Shared config materializer for Streamlit (DB mode when ``NIMBUSWARE_DATABASE_URL`` set)."""

from __future__ import annotations

import os
from pathlib import Path

from nimbusware_config import ConfigMaterializer, config_from_db_enabled


def console_config_materializer(repo_root: Path) -> ConfigMaterializer | None:
    """Return a materializer when Postgres config mode is active; else ``None`` (file fallback)."""
    if not config_from_db_enabled():
        return None
    if not os.environ.get("NIMBUSWARE_DATABASE_URL", "").strip():
        return None
    return ConfigMaterializer(repo_root)
