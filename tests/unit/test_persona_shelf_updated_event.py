from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agent_core.models import (
    EventType,
    PersonaShelfUpdatedEvent,
    PersonaShelfUpdatedPayload,
    event_envelope_adapter,
    serialize_event_persistent,
    validate_event_dict,
)
from hermes_store.allowed_types import (
    allowed_event_type_values,
    assert_event_type_registered,
)
from hermes_store.memory import InMemoryEventStore


def _ok_payload(**overrides: object) -> PersonaShelfUpdatedPayload:
    base: dict[str, object] = {
        "shelf": "business_area",
        "persona_id": "commerce",
        "prev_version": 1,
        "next_version": 2,
        "fields_changed": ["instructions"],
        "actor": "alice",
    }
    base.update(overrides)
    return PersonaShelfUpdatedPayload(**base)  # type: ignore[arg-type]


def _ok_event(**payload_overrides: object) -> PersonaShelfUpdatedEvent:
    return PersonaShelfUpdatedEvent(
        event_type=EventType.PERSONA_SHELF_UPDATED,
        event_id=uuid4(),
        run_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        payload=_ok_payload(**payload_overrides),
    )


# Axis 1: happy-path payload validates


def test_payload_happy_path_validates() -> None:
    p = _ok_payload()
    assert p.shelf == "business_area"
    assert p.persona_id == "commerce"
    assert p.next_version == 2


# Axis 2: shelf Literal rejects unknown shelves


def test_shelf_must_be_literal_subset() -> None:
    with pytest.raises(ValidationError):
        _ok_payload(shelf="archived")


# Axis 3: persona_id must be non-empty (min_length=1)


def test_persona_id_min_length_one() -> None:
    with pytest.raises(ValidationError):
        _ok_payload(persona_id="")


# Axis 4: version invariants (prev>=0, next>=1, next>prev)


def test_version_invariants_enforced() -> None:
    # next must be strictly greater than prev
    with pytest.raises(ValidationError):
        _ok_payload(prev_version=2, next_version=2)
    with pytest.raises(ValidationError):
        _ok_payload(prev_version=2, next_version=1)
    # prev_version must be >= 0
    with pytest.raises(ValidationError):
        _ok_payload(prev_version=-1, next_version=1)
    # next_version must be >= 1
    with pytest.raises(ValidationError):
        _ok_payload(prev_version=0, next_version=0)


# Axis 5: fields_changed cap at 16 entries; entries must be non-empty strings


def test_fields_changed_caps_and_string_invariants() -> None:
    with pytest.raises(ValidationError):
        _ok_payload(fields_changed=[f"f{i}" for i in range(17)])
    with pytest.raises(ValidationError):
        _ok_payload(fields_changed=[""])
    with pytest.raises(ValidationError):
        _ok_payload(fields_changed=[123])  # type: ignore[list-item]
    # The "__deleted__" sentinel is accepted (DELETE path).
    _ok_payload(fields_changed=["__deleted__"])


# Axis 6: envelope adapter round-trip preserves payload + event type


def test_event_envelope_adapter_round_trip() -> None:
    event = _ok_event()
    serialized = serialize_event_persistent(event)
    # validate_event_dict re-parses through the discriminator union
    parsed = validate_event_dict(serialized)
    assert isinstance(parsed, PersonaShelfUpdatedEvent)
    assert parsed.payload.persona_id == "commerce"
    # Adapter also accepts the dict directly
    parsed2 = event_envelope_adapter.validate_python(serialized)
    assert isinstance(parsed2, PersonaShelfUpdatedEvent)


# Axis 7: InMemoryEventStore stores + returns the event row faithfully


def test_in_memory_store_persists_persona_event() -> None:
    store = InMemoryEventStore()
    event = _ok_event(persona_id="commerce")
    store.append(event)
    rows = store.list_run_events(str(event.run_id))
    assert len(rows) == 1
    row = rows[0]
    assert row["event_type"] == EventType.PERSONA_SHELF_UPDATED.value
    assert row["payload"]["persona_id"] == "commerce"
    assert row["payload"]["fields_changed"] == ["instructions"]


# Axis 8: allowed-types registry includes the new type


def test_allowed_event_types_includes_persona_shelf_updated() -> None:
    assert "persona.shelf.updated" in allowed_event_type_values()
    # Affirmative helper does NOT raise
    assert_event_type_registered("persona.shelf.updated")
