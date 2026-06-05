"""Anti-deadlock escalation signals from ``configs/escalation/policy.yaml`` ."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from nimbusware_env.env_flags import env_str
from nimbusware_orchestrator.escalation_policy_breadth import escalation_policy_breadth
from nimbusware_orchestrator.merge import load_yaml

_PROGRESS_IGNORE: frozenset[str] = frozenset(
    {
        "run.created",
        "model.preflight.started",
        "model.preflight.passed",
        "model.preflight.failed",
        "model.selected.primary",
        "model.selected.fallback",
    },
)


def _first_run_created_at(rows: list[dict[str, Any]]) -> datetime | None:
    for r in sorted(rows, key=lambda x: int(x["store_seq"])):
        if r["event_type"] != "run.created":
            continue
        at = r.get("occurred_at")
        if isinstance(at, datetime):
            if at.tzinfo is None:
                return at.replace(tzinfo=timezone.utc)
            return at.astimezone(timezone.utc)
    return None


def count_progress_events(rows: list[dict[str, Any]]) -> int:
    """Count events that indicate the run left the pure preflight/bootstrap phase."""
    return sum(1 for r in rows if r["event_type"] not in _PROGRESS_IGNORE)


def load_anti_deadlock_settings(repo_root: Path) -> tuple[bool, int, int]:
    """Return ``(enabled, stall_minutes, min_progress_events)``."""
    breadth = escalation_policy_breadth(repo_root)
    if breadth.get("policy_load_error"):
        return False, 0, 0
    path = repo_root / "configs" / "escalation" / "policy.yaml"
    if not path.is_file():
        return False, 0, 0
    raw = load_yaml(path)
    ad = raw.get("anti_deadlock")
    if not isinstance(ad, dict):
        return False, 0, 0
    enabled = bool(ad.get("enabled", False))
    min_prog = int(ad.get("min_progress_events", 0))
    raw_min = env_str("NIMBUSWARE_DEADLOCK_ESCALATION_MINUTES")
    if raw_min:
        stall_minutes = int(raw_min)
    else:
        stall_minutes = int(raw.get("deadlock_escalation_after_minutes", 0))
    return enabled, stall_minutes, min_prog


def should_emit_anti_deadlock_escalation(
    rows: list[dict[str, Any]],
    *,
    now: datetime,
    enabled: bool,
    stall_minutes: int,
    min_progress_events: int,
) -> bool:
    if not enabled or stall_minutes <= 0:
        return False
    if any(r["event_type"] in ("run.failed", "run.completed") for r in rows):
        return False
    created = _first_run_created_at(rows)
    if created is None:
        return False
    if now - created < timedelta(minutes=stall_minutes):
        return False
    return count_progress_events(rows) < min_progress_events
