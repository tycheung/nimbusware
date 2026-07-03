from __future__ import annotations

import fnmatch
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from env.env_flags import env_truthy_on
from orchestrator.scraper_artifacts_retention import (
    RetentionAlertLevel,
    RetentionExecutionMode,
    StorageBackend,
    object_store_prune_enabled,
    retention_alert_level,
    retention_execution_mode,
)


def scraper_artifact_storage_backend_signals() -> dict[str, Any]:
    """Readiness signals for optional object-store retention (local path unchanged)."""
    from orchestrator.scraper_object_store import (
        object_store_configured,
        object_store_delete_max_attempts,
        object_store_local_mirror_enabled,
        object_store_primary_enabled,
        object_store_ready,
        object_store_timeout_seconds,
    )

    configured = object_store_configured()
    ready = object_store_ready()
    primary = object_store_primary_enabled()
    if primary:
        backend: StorageBackend = "object_store_primary"
    elif ready:
        backend = "object_store_ready"
    elif configured:
        backend = "object_store_configured"
    else:
        backend = "local"
    return {
        "storage_backend": backend,
        "object_store_configured": configured,
        "object_store_ready": ready,
        "object_store_primary": primary,
        "object_store_local_mirror": object_store_local_mirror_enabled(primary=primary),
        "object_store_timeout_seconds": object_store_timeout_seconds(),
        "object_store_delete_max_attempts": object_store_delete_max_attempts(),
        "object_store_prune_requested": env_truthy_on(
            "NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_PRUNE"
        )
        or primary,
        "object_store_prune_effective": (
            ready and env_truthy_on("NIMBUSWARE_SCRAPER_ARTIFACT_OBJECT_STORE_PRUNE")
        )
        or primary,
    }


def object_store_delete_artifact(relpath: str) -> dict[str, Any]:
    from orchestrator.scraper_object_store import object_store_delete_artifact as _delete

    return _delete(relpath)


def scraper_artifact_inventory(
    base_dir: Path,
    *,
    max_entries: int = 100,
    retention_max_age_days: int | None = None,
) -> dict[str, Any]:
    """Summarize scraper artifacts (local disk and/or object-store primary)."""
    from orchestrator.scraper_object_store import object_store_primary_enabled

    if object_store_primary_enabled():
        return _scraper_artifact_inventory_primary(
            base_dir,
            max_entries=max_entries,
            retention_max_age_days=retention_max_age_days,
        )
    return _scraper_artifact_inventory_local(
        base_dir,
        max_entries=max_entries,
        retention_max_age_days=retention_max_age_days,
    )


def _scraper_artifact_inventory_primary(
    base_dir: Path,
    *,
    max_entries: int,
    retention_max_age_days: int | None,
) -> dict[str, Any]:
    from orchestrator.scraper_object_store import (
        _file_backend_root,
        object_store_list_artifacts,
        object_store_url,
    )

    cap = max(1, int(max_entries))
    all_entries = object_store_list_artifacts(max_entries=max(cap, 5000))
    file_count = len(all_entries)
    total_bytes = sum(int(e.get("bytes", 0)) for e in all_entries)
    entries = all_entries[:cap]
    stale_file_count = 0
    stale_bytes = 0
    stale_cutoff_epoch: float | None = None
    if isinstance(retention_max_age_days, int) and retention_max_age_days >= 1:
        stale_cutoff_epoch = (
            datetime.now(timezone.utc) - timedelta(days=retention_max_age_days)
        ).timestamp()
    oldest_epoch: float | None = None
    newest_epoch: float | None = None
    for ent in all_entries:
        mtime_iso = ent.get("mtime_iso")
        if not isinstance(mtime_iso, str):
            continue
        try:
            epoch = datetime.fromisoformat(mtime_iso.replace("Z", "+00:00")).timestamp()
        except ValueError:
            continue
        if oldest_epoch is None or epoch < oldest_epoch:
            oldest_epoch = epoch
        if newest_epoch is None or epoch > newest_epoch:
            newest_epoch = epoch
        if stale_cutoff_epoch is not None and epoch < stale_cutoff_epoch:
            stale_file_count += 1
            stale_bytes += int(ent.get("bytes", 0))
    root = _file_backend_root()
    resolved = base_dir.expanduser().resolve()
    out: dict[str, Any] = {
        "base_dir": str(root) if root is not None else object_store_url() or str(resolved),
        "exists": file_count > 0 or (root is not None and root.is_dir()),
        "file_count": file_count,
        "total_bytes": total_bytes,
        "truncated": file_count > len(entries),
        "entries": entries,
        "retention_stale_file_count": stale_file_count,
        "retention_stale_bytes": stale_bytes,
        "oldest_mtime_iso": None,
        "newest_mtime_iso": None,
    }
    if oldest_epoch is not None:
        out["oldest_mtime_iso"] = (
            datetime.fromtimestamp(oldest_epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        )
    if newest_epoch is not None:
        out["newest_mtime_iso"] = (
            datetime.fromtimestamp(newest_epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        )
    out.update(scraper_artifact_storage_backend_signals())
    out["retention_execution_mode"] = retention_execution_mode()
    out["retention_alert_level"] = retention_alert_level(
        retention_stale_file_count=stale_file_count,
        retention_stale_bytes=stale_bytes,
        retention_max_age_days=retention_max_age_days,
    )
    return out


def _scraper_artifact_inventory_local(
    base_dir: Path,
    *,
    max_entries: int,
    retention_max_age_days: int | None,
) -> dict[str, Any]:
    """Summarize on-disk scraper artifacts (read-only; safe when ``base_dir`` is missing)."""
    cap = max(1, int(max_entries))
    resolved = base_dir.expanduser().resolve()
    out: dict[str, Any] = {
        "base_dir": str(resolved),
        "exists": resolved.exists(),
        "file_count": 0,
        "total_bytes": 0,
        "truncated": False,
        "oldest_mtime_iso": None,
        "newest_mtime_iso": None,
        "retention_stale_file_count": 0,
        "retention_stale_bytes": 0,
        "entries": [],
    }
    out.update(scraper_artifact_storage_backend_signals())
    out["retention_execution_mode"] = retention_execution_mode()
    if not resolved.is_dir():
        out["retention_alert_level"] = "none"
        return out
    entries: list[dict[str, Any]] = []
    file_count = 0
    total_bytes = 0
    oldest_epoch: float | None = None
    newest_epoch: float | None = None
    stale_cutoff_epoch: float | None = None
    stale_file_count = 0
    stale_bytes = 0
    if isinstance(retention_max_age_days, int) and retention_max_age_days >= 1:
        stale_cutoff_epoch = (
            datetime.now(timezone.utc) - timedelta(days=retention_max_age_days)
        ).timestamp()
    for path in sorted(resolved.rglob("*")):
        if not path.is_file():
            continue
        file_count += 1
        try:
            st = path.stat()
        except OSError:
            continue
        total_bytes += st.st_size
        if oldest_epoch is None or st.st_mtime < oldest_epoch:
            oldest_epoch = st.st_mtime
        if newest_epoch is None or st.st_mtime > newest_epoch:
            newest_epoch = st.st_mtime
        if stale_cutoff_epoch is not None and st.st_mtime < stale_cutoff_epoch:
            stale_file_count += 1
            stale_bytes += st.st_size
        if len(entries) < cap:
            mtime = (
                datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
                .isoformat()
                .replace(
                    "+00:00",
                    "Z",
                )
            )
            entries.append(
                {
                    "relpath": path.relative_to(resolved).as_posix(),
                    "bytes": st.st_size,
                    "mtime_iso": mtime,
                },
            )
    out["file_count"] = file_count
    out["total_bytes"] = total_bytes
    out["entries"] = entries
    out["truncated"] = file_count > len(entries)
    out["retention_stale_file_count"] = stale_file_count
    out["retention_stale_bytes"] = stale_bytes
    if oldest_epoch is not None:
        out["oldest_mtime_iso"] = (
            datetime.fromtimestamp(oldest_epoch, tz=timezone.utc)
            .isoformat()
            .replace(
                "+00:00",
                "Z",
            )
        )
    if newest_epoch is not None:
        out["newest_mtime_iso"] = (
            datetime.fromtimestamp(newest_epoch, tz=timezone.utc)
            .isoformat()
            .replace(
                "+00:00",
                "Z",
            )
        )
    out["retention_alert_level"] = retention_alert_level(
        retention_stale_file_count=stale_file_count,
        retention_stale_bytes=stale_bytes,
        retention_max_age_days=retention_max_age_days,
    )
    return out
