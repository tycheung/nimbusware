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

RUN_ESCALATED_DELTA_FIELDS: tuple[tuple[str, str], ...] = (
    ("previous_event_id", "Previous event id"),
    ("current_event_id", "Current event id"),
    ("reason_code_changed", "Reason code changed"),
    ("actor_id_changed", "Actor id changed"),
    ("policy_snapshot_id_changed", "Policy snapshot id changed"),
    ("previous_reason_code", "Previous reason code"),
    ("current_reason_code", "Current reason code"),
    ("previous_actor_id", "Previous actor id"),
    ("current_actor_id", "Current actor id"),
)

__all__ = [
    "RUN_ESCALATED_DELTA_FIELDS",
    "RUN_ESCALATED_DISPLAY_FIELDS",
    "RUN_ESCALATED_ROW_KEYS",
]
