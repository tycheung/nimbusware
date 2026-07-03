from __future__ import annotations

from agent_core.models import EventType


def allowed_event_type_values() -> tuple[str, ...]:
    return tuple(sorted(e.value for e in EventType))


def assert_event_type_registered(event_type: str) -> None:
    allowed = frozenset(allowed_event_type_values())
    if event_type not in allowed:
        msg = f"event_type {event_type!r} not in EventType / DB allowlist"
        raise ValueError(msg)
