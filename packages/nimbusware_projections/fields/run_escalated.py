"""Run escalated projection field metadata."""

from __future__ import annotations

RUN_ESCALATED_ROW_KEYS: tuple[str, ...] = (
    "event_id",
    "occurred_at",
    "actor_id",
    "reason_code",
    "policy_snapshot_id",
    "notes",
)

RUN_ESCALATED_DISPLAY_FIELDS: tuple[tuple[str, str], ...] = (
    ("actor_id", "Actor id"),
    ("reason_code", "Reason code"),
    ("policy_snapshot_id", "Policy snapshot id"),
    ("notes", "Notes"),
    ("event_id", "Event id"),
    ("occurred_at", "Occurred at"),
)

__all__ = ["RUN_ESCALATED_DISPLAY_FIELDS", "RUN_ESCALATED_ROW_KEYS"]
