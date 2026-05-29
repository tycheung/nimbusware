"""On-disk scraper response artifact helpers."""

from __future__ import annotations

import fnmatch
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

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


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _int_env(name: str, default: int, *, minimum: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        parsed = int(raw)
    except ValueError:
        return default
    return max(parsed, minimum)


def object_store_prune_enabled() -> bool:
    """Mirror local deletes to object store when store is ready and env is on."""
    from hermes_orchestrator.scraper_object_store import object_store_primary_enabled

    if object_store_primary_enabled():
        return True
    if not _truthy_env("HERMES_SCRAPER_ARTIFACT_OBJECT_STORE_PRUNE"):
        return False
    return scraper_artifact_storage_backend_signals()["storage_backend"] == "object_store_ready"


def retention_execution_mode() -> RetentionExecutionMode:
    from hermes_orchestrator.scraper_object_store import object_store_primary_enabled

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


def scraper_artifact_storage_backend_signals() -> dict[str, Any]:
    """Readiness signals for optional object-store retention (local path unchanged)."""
    from hermes_orchestrator.scraper_object_store import (
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
        "object_store_prune_requested": _truthy_env("HERMES_SCRAPER_ARTIFACT_OBJECT_STORE_PRUNE")
        or primary,
        "object_store_prune_effective": (ready and _truthy_env("HERMES_SCRAPER_ARTIFACT_OBJECT_STORE_PRUNE"))
        or primary,
    }


def object_store_delete_artifact(relpath: str) -> dict[str, Any]:
    """Best-effort DELETE for one artifact key (no-op when store not ready)."""
    from hermes_orchestrator.scraper_object_store import object_store_delete_artifact as _delete

    return _delete(relpath)


def scraper_artifact_inventory(
    base_dir: Path,
    *,
    max_entries: int = 100,
    retention_max_age_days: int | None = None,
) -> dict[str, Any]:
    """Summarize scraper artifacts (local disk and/or object-store primary)."""
    from hermes_orchestrator.scraper_object_store import object_store_primary_enabled

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
    from hermes_orchestrator.scraper_object_store import (
        _file_backend_root,
        object_store_list_artifacts,
        object_store_local_mirror_enabled,
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
            mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat().replace(
                "+00:00",
                "Z",
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
            datetime.fromtimestamp(oldest_epoch, tz=timezone.utc).isoformat().replace(
                "+00:00",
                "Z",
            )
        )
    if newest_epoch is not None:
        out["newest_mtime_iso"] = (
            datetime.fromtimestamp(newest_epoch, tz=timezone.utc).isoformat().replace(
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


def persist_scraper_artifact(
    repo_root: Path,
    run_id: UUID,
    url_index: int,
    content: bytes,
    persist_cap: int,
) -> dict[str, Any]:
    """Persist scraper response artifact (object-store primary or local)."""
    import hashlib

    from hermes_orchestrator.scraper_object_store import (
        object_store_local_mirror_enabled,
        object_store_primary_enabled,
        object_store_put_artifact,
    )

    blob = content[:persist_cap]
    digest_full = hashlib.sha256(content).hexdigest()
    fname = f"url{url_index:02d}_{digest_full[:32]}.bin"
    relpath = f"{run_id}/{fname}"
    primary = object_store_primary_enabled()
    if primary:
        put = object_store_put_artifact(relpath, blob)
        if not put.get("stored"):
            msg = f"object store put failed: {put.get('error')}"
            raise RuntimeError(msg)
        if object_store_local_mirror_enabled(primary=True):
            base_dir = resolve_scraper_artifact_base_dir(repo_root)
            base_dir.mkdir(parents=True, exist_ok=True)
            out_path = base_dir / relpath.replace("/", os.sep)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(blob)
        artifact_digest = hashlib.sha256(blob).hexdigest()
        return {
            "artifact_relpath": relpath,
            "artifact_sha256": artifact_digest,
            "artifact_bytes_written": len(blob),
            "storage_authority": "object_store_primary",
        }
    base_dir = resolve_scraper_artifact_base_dir(repo_root)
    base_dir.mkdir(parents=True, exist_ok=True)
    run_dir = base_dir / str(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / fname
    out_path.write_bytes(blob)
    artifact_digest = hashlib.sha256(blob).hexdigest()
    try:
        rel = out_path.relative_to(base_dir)
    except ValueError:
        rel = Path(fname)
    return {
        "artifact_relpath": str(rel).replace("\\", "/"),
        "artifact_sha256": artifact_digest,
        "artifact_bytes_written": len(blob),
        "storage_authority": "local",
    }


def resolve_scraper_artifact_base_dir(repo_root: Path) -> Path:
    """Match ``RunOrchestrator._persist_scraper_response_artifact`` base directory."""
    raw = os.environ.get("HERMES_SCRAPER_ARTIFACT_DIR", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (repo_root / ".cache" / "hermes_scraper").resolve()


def _matches_any(name: str, patterns: list[str] | None) -> bool:
    """``True`` when ``name`` matches at least one glob in ``patterns``.

    ``None`` and empty lists are treated as "no match" so callers can rely on
    ``if patterns and _matches_any(...)`` for the "any-match" branch and
    ``if patterns and not _matches_any(...)`` for the "must-match-one" branch
    without juggling ``None`` checks.
    """
    if not patterns:
        return False
    return any(fnmatch.fnmatch(name, p) for p in patterns)


def prune_scraper_artifacts(
    base_dir: Path,
    *,
    max_age_days: int,
    now: datetime | None = None,
    dry_run: bool = False,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    force_local: bool = False,
) -> dict[str, Any]:
    """Delete regular files under ``base_dir`` older than ``max_age_days`` (mtime, UTC).

    Returns a structured result with ``local_removed``, object-store mirror counts,
    and ``retention_execution_mode``. Missing ``base_dir`` is a no-op.

    When ``dry_run`` is true, counts stale files but does not delete them and does not
    remove empty directories (non-destructive preview).

    ``include_patterns`` / ``exclude_patterns``: optional ``fnmatch`` glob
    lists evaluated against each file's BASENAME after the mtime cutoff filter.

    ``force_local`` skips object-store-primary dispatch (local mirror cleanup only).
    """
    if max_age_days < 1:
        msg = "max_age_days must be >= 1"
        raise ValueError(msg)
    from hermes_orchestrator.scraper_object_store import object_store_primary_enabled

    if not force_local and object_store_primary_enabled():
        return _prune_scraper_artifacts_primary(
            base_dir,
            max_age_days=max_age_days,
            now=now,
            dry_run=dry_run,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
        )
    mode = retention_execution_mode()
    mirror = object_store_prune_enabled() and not dry_run
    result: dict[str, Any] = {
        "local_removed": 0,
        "object_store_attempted": 0,
        "object_store_removed": 0,
        "object_store_failed": 0,
        "object_store_last_error": None,
        "retention_execution_mode": mode,
        "retention_stale_file_count": 0,
        "retention_stale_bytes": 0,
        "retention_alert_level": "none",
        "retention_lifecycle_state": "healthy",
        "retention_max_age_days": max_age_days,
    }
    if not base_dir.exists():
        return result
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=max_age_days)
    paths = sorted(base_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True)
    for path in paths:
        if not path.is_file():
            continue
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if mtime >= cutoff:
            continue
        if include_patterns and not _matches_any(path.name, include_patterns):
            continue
        if _matches_any(path.name, exclude_patterns):
            continue
        result["retention_stale_file_count"] += 1
        result["retention_stale_bytes"] += int(path.stat().st_size)
        relpath = path.relative_to(base_dir).as_posix()
        if not dry_run:
            path.unlink(missing_ok=True)
            if mirror:
                os_result = object_store_delete_artifact(relpath)
                if os_result.get("attempted"):
                    result["object_store_attempted"] += 1
                if os_result.get("deleted"):
                    result["object_store_removed"] += 1
                elif os_result.get("attempted"):
                    result["object_store_failed"] += 1
                    if os_result.get("error"):
                        result["object_store_last_error"] = str(os_result["error"])
        result["local_removed"] += 1
    result["retention_alert_level"] = retention_alert_level(
        retention_stale_file_count=int(result["retention_stale_file_count"]),
        retention_stale_bytes=int(result["retention_stale_bytes"]),
        retention_max_age_days=max_age_days,
    )
    object_store_failed = int(result["object_store_failed"])
    if object_store_failed > 0:
        result["retention_lifecycle_state"] = "mirror_degraded"
    elif dry_run:
        result["retention_lifecycle_state"] = "dry_run_preview"
    elif int(result["local_removed"]) > 0:
        result["retention_lifecycle_state"] = "pruned"
    elif int(result["retention_stale_file_count"]) > 0:
        result["retention_lifecycle_state"] = "stale_pending"
    if dry_run:
        return result
    for path in sorted(base_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass
    return result


def _prune_scraper_artifacts_primary(
    base_dir: Path,
    *,
    max_age_days: int,
    now: datetime | None,
    dry_run: bool,
    include_patterns: list[str] | None,
    exclude_patterns: list[str] | None,
) -> dict[str, Any]:
    from hermes_orchestrator.scraper_object_store import (
        object_store_list_artifacts,
        object_store_local_mirror_enabled,
    )

    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=max_age_days)
    result: dict[str, Any] = {
        "local_removed": 0,
        "object_store_attempted": 0,
        "object_store_removed": 0,
        "object_store_failed": 0,
        "object_store_last_error": None,
        "retention_execution_mode": "object_store_primary",
        "retention_stale_file_count": 0,
        "retention_stale_bytes": 0,
        "retention_alert_level": "none",
        "retention_lifecycle_state": "healthy",
        "retention_max_age_days": max_age_days,
    }
    for ent in object_store_list_artifacts(max_entries=10000):
        relpath = str(ent.get("relpath", ""))
        if not relpath:
            continue
        basename = Path(relpath).name
        mtime_iso = ent.get("mtime_iso")
        if not isinstance(mtime_iso, str):
            continue
        try:
            mtime = datetime.fromisoformat(mtime_iso.replace("Z", "+00:00"))
        except ValueError:
            continue
        if mtime >= cutoff:
            continue
        if include_patterns and not _matches_any(basename, include_patterns):
            continue
        if _matches_any(basename, exclude_patterns):
            continue
        result["retention_stale_file_count"] += 1
        result["retention_stale_bytes"] += int(ent.get("bytes", 0))
        if not dry_run:
            os_result = object_store_delete_artifact(relpath)
            if os_result.get("attempted"):
                result["object_store_attempted"] += 1
            if os_result.get("deleted"):
                result["object_store_removed"] += 1
            elif os_result.get("attempted"):
                result["object_store_failed"] += 1
                if os_result.get("error"):
                    result["object_store_last_error"] = str(os_result["error"])
        result["local_removed"] += 1
    if not dry_run and object_store_local_mirror_enabled(primary=True) and base_dir.exists():
        local_result = prune_scraper_artifacts(
            base_dir,
            max_age_days=max_age_days,
            now=now,
            dry_run=False,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            force_local=True,
        )
        result["local_mirror_removed"] = int(local_result.get("local_removed", 0))
    result["retention_alert_level"] = retention_alert_level(
        retention_stale_file_count=int(result["retention_stale_file_count"]),
        retention_stale_bytes=int(result["retention_stale_bytes"]),
        retention_max_age_days=max_age_days,
    )
    if int(result["object_store_failed"]) > 0:
        result["retention_lifecycle_state"] = "mirror_degraded"
    elif dry_run:
        result["retention_lifecycle_state"] = "dry_run_preview"
    elif int(result["local_removed"]) > 0:
        result["retention_lifecycle_state"] = "pruned"
    elif int(result["retention_stale_file_count"]) > 0:
        result["retention_lifecycle_state"] = "stale_pending"
    return result


def prune_scraper_artifacts_local_removed(
    base_dir: Path,
    *,
    max_age_days: int,
    now: datetime | None = None,
    dry_run: bool = False,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> int:
    """Backward-compatible int return (local_removed only)."""
    return int(
        prune_scraper_artifacts(
            base_dir,
            max_age_days=max_age_days,
            now=now,
            dry_run=dry_run,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
        )["local_removed"],
    )
