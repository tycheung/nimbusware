"""Shared persona shelf audit helpers.

``persona_catalog_run_id`` MUST stay aligned with
``packages/api/routes/personas.py`` so API and orchestrator writes share
the same synthetic run id for ``persona.shelf.updated`` history queries.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4, uuid5

from agent_core.models import (
    EventType,
    PersonaShelfUpdatedEvent,
    PersonaShelfUpdatedPayload,
)
from extensions.personas import ALLOWED_SHELVES
from store.protocol import EventStore

_PERSONA_RUN_NAMESPACE = UUID("00000000-0000-5000-8000-000000000001")


def persona_catalog_run_id(shelf: str, persona_id: str) -> UUID:
    return uuid5(_PERSONA_RUN_NAMESPACE, f"{shelf}/{persona_id}")


def append_persona_shelf_updated_event(
    store: EventStore,
    *,
    shelf: str,
    persona_id: str,
    prev_version: int,
    next_version: int,
    fields_changed: list[str],
    actor: str | None,
    correlation_id: UUID | None,
) -> None:
    if shelf not in ALLOWED_SHELVES:
        raise ValueError(f"invalid persona shelf {shelf!r}")
    store.append(
        PersonaShelfUpdatedEvent(
            event_type=EventType.PERSONA_SHELF_UPDATED,
            event_id=uuid4(),
            run_id=persona_catalog_run_id(shelf, persona_id),
            occurred_at=datetime.now(timezone.utc),
            correlation_id=correlation_id,
            payload=PersonaShelfUpdatedPayload(
                shelf=shelf,  # type: ignore[arg-type]
                persona_id=persona_id,
                prev_version=prev_version,
                next_version=next_version,
                fields_changed=fields_changed,
                actor=actor,
            ),
        ),
    )
