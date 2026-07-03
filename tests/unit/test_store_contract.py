from __future__ import annotations

import re
from pathlib import Path

import pytest

from agent_core.models import EventType
from env import find_repo_root
from store.allowed_types import allowed_event_type_values, assert_event_type_registered
from store.memory import InMemoryEventStore
from store.protocol import EventStore

_SCHEMA_SQL = (
    find_repo_root(start=Path(__file__).resolve().parents[1])
    / "packages"
    / "store"
    / "schema"
    / "postgres.sql"
)


def _event_type_check_list_from_schema() -> set[str] | None:
    text = _SCHEMA_SQL.read_text(encoding="utf-8")
    pattern = re.compile(
        r"CONSTRAINT event_store_type_allowed CHECK \(event_type IN \(([^)]+)\)\)",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None
    return set(re.findall(r"'([^']+)'", match.group(1)))


def test_in_memory_event_store_satisfies_event_store_protocol() -> None:
    store = InMemoryEventStore()
    assert isinstance(store, EventStore)


def test_allowed_event_type_values_matches_event_type_enum() -> None:
    from_code = set(allowed_event_type_values())
    from_enum = {member.value for member in EventType}
    assert from_code == from_enum
    assert tuple(sorted(from_code)) == allowed_event_type_values()


def test_allowed_event_types_match_postgres_schema_check_list() -> None:
    listed = _event_type_check_list_from_schema()
    assert listed is not None, (
        f"No CONSTRAINT event_store_type_allowed CHECK (event_type IN (...)) found in {_SCHEMA_SQL}"
    )
    from_code = set(allowed_event_type_values())
    assert listed == from_code, (listed - from_code, from_code - listed)


def test_assert_event_type_registered_rejects_unknown_type() -> None:
    with pytest.raises(ValueError, match="not in EventType"):
        assert_event_type_registered("not.a.real.event")
