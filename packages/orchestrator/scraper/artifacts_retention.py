from __future__ import annotations

from typing import Literal

from env.env_flags import env_truthy_on

StorageBackend = Literal[
    "local",
    "object_store_configured",
    "object_store_ready",
    "object_store_primary",
]
RetentionExecutionMode = Literal[
    "local_only",
    "local_with_object_store_mirror",
    "object_store_primary",
]
RetentionAlertLevel = Literal["none", "stale_present", "stale_high"]

_STALE_HIGH_BYTES = 10 * 1024 * 1024
_STALE_HIGH_FILE_COUNT = 100


def object_store_prune_enabled() -> bool:
    """Mirror local deletes to object store when store is ready and env is on."""
    from orchestrator.scraper.object_store import object_store_primary_enabled

    if object_store_primary_enabled():
        return True
    if not env_truthy_on("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_PRUNE"):
        return False
    from orchestrator.scraper.artifacts_inventory import (
        scraper_artifact_storage_backend_signals,
    )

    signals = scraper_artifact_storage_backend_signals()
    return bool(signals.get("storage_backend") == "object_store_ready")


def retention_execution_mode() -> RetentionExecutionMode:
    from orchestrator.scraper.object_store import object_store_primary_enabled

    if object_store_primary_enabled():
        return "object_store_primary"
    if object_store_prune_enabled():
        return "local_with_object_store_mirror"
    return "local_only"


def retention_alert_level(
    *,
    retention_stale_file_count: int,
    retention_stale_bytes: int,
    retention_max_age_days: int | None,
) -> RetentionAlertLevel:
    if retention_max_age_days is None or retention_max_age_days < 1:
        return "none"
    if retention_stale_file_count <= 0:
        return "none"
    if (
        retention_stale_bytes >= _STALE_HIGH_BYTES
        or retention_stale_file_count >= _STALE_HIGH_FILE_COUNT
    ):
        return "stale_high"
    return "stale_present"
