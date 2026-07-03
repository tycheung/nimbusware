from __future__ import annotations

import fnmatch
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from env.env_flags import env_str
from orchestrator.scraper.artifacts_inventory import (
    object_store_delete_artifact,
)
from orchestrator.scraper.artifacts_retention import (
    object_store_prune_enabled,
    retention_alert_level,
    retention_execution_mode,
)


def persist_scraper_artifact(
    repo_root: Path,
    run_id: UUID,
    url_index: int,
    content: bytes,
    persist_cap: int,
) -> dict[str, Any]:
    """Persist scraper response artifact (object-store primary or local)."""
    import hashlib

    from orchestrator.scraper.object_store import (
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
    raw = env_str("NIMBUSWARE_SCRAPER_ARTIFACT_DIR")
    if raw:
        return Path(raw).expanduser().resolve()
    return (repo_root / ".cache" / "nimbusware_scraper").resolve()


def _matches_any(name: str, patterns: list[str] | None) -> bool:
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
    if max_age_days < 1:
        msg = "max_age_days must be >= 1"
        raise ValueError(msg)
    from orchestrator.scraper.object_store import object_store_primary_enabled

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
    from orchestrator.scraper.object_store import (
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
