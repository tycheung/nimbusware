from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ScraperArtifactInventoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relpath: str
    bytes: int = Field(ge=0)
    mtime_iso: str


class ScraperArtifactInventoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_dir: str
    exists: bool
    file_count: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    truncated: bool
    oldest_mtime_iso: str | None = None
    newest_mtime_iso: str | None = None
    retention_max_age_days: int | None = Field(default=None, ge=1)
    retention_stale_file_count: int = Field(default=0, ge=0)
    retention_stale_bytes: int = Field(default=0, ge=0)
    storage_backend: Literal[
        "local",
        "object_store_configured",
        "object_store_ready",
        "object_store_primary",
    ] = "local"
    object_store_configured: bool = False
    object_store_ready: bool = False
    object_store_primary: bool = False
    object_store_local_mirror: bool = True
    object_store_timeout_seconds: int = Field(default=30, ge=1)
    object_store_delete_max_attempts: int = Field(default=1, ge=1)
    object_store_prune_requested: bool = False
    object_store_prune_effective: bool = False
    retention_execution_mode: Literal[
        "local_only",
        "local_with_object_store_mirror",
        "object_store_primary",
    ] = "local_only"
    retention_alert_level: Literal["none", "stale_present", "stale_high"] = "none"
    entries: list[ScraperArtifactInventoryEntry]
