"""Feature flags for Postgres vs file-backed configuration."""

from __future__ import annotations

from nimbusware_env.env_flags import (
    nimbusware_config_from_db_enabled,
    nimbusware_config_notify_enabled,
)


def config_from_db_enabled() -> bool:
    return nimbusware_config_from_db_enabled()


def config_notify_enabled() -> bool:
    return nimbusware_config_notify_enabled()
