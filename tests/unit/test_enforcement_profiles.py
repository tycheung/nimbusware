from __future__ import annotations

from orchestrator.profiles.enforcement_profiles import (
    default_enforcement_level_for_work_type,
    enforcement_effective_metadata,
    enforcement_profile_from_rows,
    persist_run_enforcement,
    preset_for_enforcement_level,
    resolve_enforcement_profile,
)


def test_preset_levels_increase_strictness() -> None:
    low = preset_for_enforcement_level(0)
    mid = preset_for_enforcement_level(5)
    high = preset_for_enforcement_level(10)
    assert low.ruff_scope == "off"
    assert mid.tests_mode == "mapped_required"
    assert high.terminal_parity_ci is True
    assert high.ruff_format_check is True


def test_default_enforcement_level_for_work_type() -> None:
    assert default_enforcement_level_for_work_type("patch") == 4
    assert default_enforcement_level_for_work_type("factory") == 7
    assert default_enforcement_level_for_work_type("slice") == 5
    meta = enforcement_effective_metadata("patch")
    assert meta["level"] == 4
    assert meta["source"] == "work_type_default"


def test_resolve_custom_overrides() -> None:
    profile = resolve_enforcement_profile(level=5, custom_overrides={"coverage_floor": 0.9})
    assert profile.custom is True
    assert profile.coverage_floor == 0.9


def test_persist_and_read_from_rows() -> None:
    from uuid import uuid4

    from store.memory import InMemoryEventStore

    store = InMemoryEventStore()
    run_id = uuid4()
    profile = preset_for_enforcement_level(8)
    persist_run_enforcement(store, run_id, profile)
    rows = store.list_run_events(str(run_id))
    loaded = enforcement_profile_from_rows(rows)
    assert loaded.level == 8
    assert loaded.ruff_format_check is True
