from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from agent_core.coercion import is_strict_int

SCRAPER_ARTIFACT_PRUNE_WORKFLOW_RELPATH = ".github/workflows/scraper_artifact_prune.yml"


from console.prune_status_display.status_captions import _parse_wrote_at


def scraper_artifact_inventory_storage_caption(
    inventory: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(inventory, Mapping):
        return None
    backend = inventory.get("storage_backend")
    if not isinstance(backend, str) or not backend.strip():
        return None
    configured = inventory.get("object_store_configured")
    ready = inventory.get("object_store_ready")
    prune_requested = inventory.get("object_store_prune_requested")
    prune_effective = inventory.get("object_store_prune_effective")
    timeout_seconds = inventory.get("object_store_timeout_seconds")
    delete_attempts = inventory.get("object_store_delete_max_attempts")
    parts = [f"backend={backend.strip()}"]
    if isinstance(configured, bool):
        parts.append(f"configured={configured}")
    if isinstance(ready, bool):
        parts.append(f"ready={ready}")
    if isinstance(prune_requested, bool):
        parts.append(f"prune_requested={prune_requested}")
    if isinstance(prune_effective, bool):
        parts.append(f"prune_effective={prune_effective}")
    if is_strict_int(timeout_seconds):
        parts.append(f"timeout_s={timeout_seconds}")
    if is_strict_int(delete_attempts):
        parts.append(f"delete_attempts={delete_attempts}")
    return "Scraper artifact storage: " + ", ".join(parts) + "."


def prune_status_wrote_at_caption(
    status: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(status, Mapping):
        return None
    raw = status.get("wrote_at")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"Prune status wrote_at: `{text}`."


def prune_status_dry_run_caption(
    status: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(status, Mapping):
        return None
    dry = status.get("dry_run")
    if dry is True:
        return "Prune dry_run: **yes** (no paths removed on disk)."
    if dry is False:
        return "Prune dry_run: **no** (paths may have been removed)."
    return None


def prune_status_pruned_outcome_caption(
    status: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(status, Mapping):
        return None
    pruned = status.get("pruned")
    if not isinstance(pruned, int) or isinstance(pruned, bool) or pruned < 0:
        return None
    dry = status.get("dry_run")
    if dry is True:
        dry_label = "yes"
    elif dry is False:
        dry_label = "no"
    else:
        dry_label = "unknown"
    suffix = "path" if pruned == 1 else "paths"
    return f"Last prune: **{pruned}** {suffix} removed, dry_run=**{dry_label}**."


def prune_status_base_dir_caption(
    status: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(status, Mapping):
        return None
    raw = status.get("base")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"Prune base directory: `{text}`."


def prune_status_freshness_caption(
    status: Mapping[str, Any] | None,
    *,
    now: datetime | None = None,
    stale_after_hours: int = 24,
) -> str:
    if not status:
        return (
            "No prune status file yet (run scripts/ops/prune_scraper_artifacts.py "
            "with --summary-path or NIMBUSWARE_PRUNE_STATUS_PATH set)."
        )
    wrote_at = _parse_wrote_at(status.get("wrote_at"))
    if wrote_at is None:
        return "Status file present but missing wrote_at timestamp."
    if wrote_at.tzinfo is None:
        wrote_at = wrote_at.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    delta = current - wrote_at
    total_seconds = max(int(delta.total_seconds()), 0)
    if total_seconds < 60:
        age = f"{total_seconds} second{'s' if total_seconds != 1 else ''}"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        age = f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        hours = total_seconds // 3600
        age = f"{hours} hour{'s' if hours != 1 else ''}"
    stale_suffix = (
        f" Stale (>{stale_after_hours}h)." if total_seconds > stale_after_hours * 3600 else ""
    )
    return f"Last updated {age} ago.{stale_suffix}"
