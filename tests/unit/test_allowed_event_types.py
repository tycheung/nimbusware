from __future__ import annotations

import re
from pathlib import Path

from nimbusware_env import find_repo_root
from nimbusware_store.allowed_types import allowed_event_type_values

_SCHEMA_SQL = (
    find_repo_root(start=Path(__file__).resolve().parents[1])
    / "packages"
    / "nimbusware_store"
    / "schema"
    / "postgres.sql"
)


def _event_type_check_list_from_schema() -> set[str] | None:
    """Parse the single ``CHECK (event_type IN (...))`` from ``postgres.sql``."""
    text = _SCHEMA_SQL.read_text(encoding="utf-8")
    pattern = re.compile(
        r"CONSTRAINT event_store_type_allowed CHECK \(event_type IN \(([^)]+)\)\)",
        re.DOTALL | re.IGNORECASE,
    )
    m = pattern.search(text)
    if not m:
        return None
    return set(re.findall(r"'([^']+)'", m.group(1)))


def test_event_types_match_schema_check_list() -> None:
    listed = _event_type_check_list_from_schema()
    assert listed is not None, (
        f"No CONSTRAINT event_store_type_allowed CHECK (event_type IN (...)) found in {_SCHEMA_SQL}"
    )
    from_code = set(allowed_event_type_values())
    assert listed == from_code, (listed - from_code, from_code - listed)
