from __future__ import annotations

from typing import Any
from uuid import UUID

from agent_core.models import validate_event_dict
from store.protocol import EventStore, serialized_event_from_row


def baseline_event_ids(store: EventStore, run_id: UUID) -> set[str]:
    return {str(row["event_id"]) for row in store.list_run_events(str(run_id))}


def collect_replay_events(
    store: EventStore,
    run_id: UUID,
    baseline_ids: set[str],
) -> list[dict[str, Any]]:
    rows = store.list_run_events(str(run_id))
    out: list[dict[str, Any]] = []
    for row in rows:
        event_id = str(row["event_id"])
        if event_id in baseline_ids:
            continue
        out.append(serialized_event_from_row(row))
    return out


def replay_events_to_store(
    store: EventStore,
    run_id: UUID,
    events: list[dict[str, Any]],
) -> int:
    existing = {str(row["event_id"]) for row in store.list_run_events(str(run_id))}
    appended = 0
    for raw in events:
        if not isinstance(raw, dict):
            continue
        event_id = str(raw.get("event_id") or "")
        if not event_id or event_id in existing:
            continue
        store.append(validate_event_dict(raw))
        existing.add(event_id)
        appended += 1
    return appended
