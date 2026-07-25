"""Thin mesh event replay (`sak417-c` / `sak432-c`).

Legacy under ``=0``. Non-absorb paths refuse when COMPUTE enabled (``=1|2``).
Absorb helpers remain allowed under ``=2``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from broker_client.flags import broker_compute_enabled
from store.protocol import EventStore

_MSG = (
    "compute mesh_event_replay local path unavailable under NIMBUSWARE_BROKER_COMPUTE=1|2; "
    "use SwissArmyNoife compute_work"
)


def _guard() -> None:
    if broker_compute_enabled():
        raise RuntimeError(_MSG)


def _legacy():
    from compute import mesh_event_replay_legacy as legacy

    return legacy


def baseline_event_ids(store: EventStore, run_id: UUID) -> set[str]:
    _guard()
    return _legacy().baseline_event_ids(store, run_id)


def collect_replay_events(
    store: EventStore,
    run_id: UUID,
    baseline_ids: set[str],
) -> list[dict[str, Any]]:
    _guard()
    return _legacy().collect_replay_events(store, run_id, baseline_ids)


def replay_events_to_store(
    store: EventStore,
    run_id: UUID,
    events: list[dict[str, Any]],
) -> int:
    _guard()
    return _legacy().replay_events_to_store(store, run_id, events)


def replay_events_to_store_absorb(
    store: EventStore,
    run_id: UUID,
    events: list[dict[str, Any]],
) -> int:
    """Absorb-safe replay — allowed under COMPUTE=1|2 (`sak425-c` / `sak432-c`)."""
    return _legacy().replay_events_to_store(store, run_id, events)
