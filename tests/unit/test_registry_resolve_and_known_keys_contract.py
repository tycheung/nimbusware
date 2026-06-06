from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from nimbusware_orchestrator.registry import RoleRegistry


def _uuid() -> UUID:
    return uuid4()


def test_resolve_strip_lower_input_symmetry_5_axis() -> None:
    uuid_a = _uuid()
    uuid_b = _uuid()
    reg = RoleRegistry.from_mapping({"backendwriter": uuid_a, "planner": uuid_b})

    assert reg.resolve("backendwriter") == uuid_a, (
        "A1: exact lowercase key must return its stored UUID"
    )
    assert reg.resolve("BackendWriter") == uuid_a, (
        "A2: mixed-case input must normalize via .lower() and resolve"
    )
    assert reg.resolve("  backendwriter  ") == uuid_a, (
        "A3: whitespace-wrapped input must normalize via .strip() and resolve"
    )
    assert reg.resolve("\t  BACKENDWRITER \n") == uuid_a, (
        "A4: combined messy input must normalize via .strip().lower() chained"
    )
    assert reg.resolve("planner") == uuid_b, (
        "A5: multi-key registry must return the UUID matching the resolved key, "
        "not a shared singleton"
    )
    assert uuid_a != uuid_b, (
        "A5 precondition: the two test UUIDs must be distinct so the prior assertion is non-trivial"
    )


def test_resolve_keyerror_direct_message_contract_5_axis() -> None:
    reg = RoleRegistry.from_mapping({"planner": _uuid()})

    with pytest.raises(KeyError) as exc_b1:
        reg.resolve("backend_writer")
    assert exc_b1.value.args[0] == "Unknown role taxonomy_key: 'backend_writer'", (
        "B1: KeyError args[0] must be the exact f-string with !r repr of input"
    )

    empty_reg = RoleRegistry.from_mapping({})
    with pytest.raises(KeyError) as exc_b2:
        empty_reg.resolve("anything")
    assert exc_b2.value.args[0] == "Unknown role taxonomy_key: 'anything'", (
        "B2: empty registry must raise KeyError for any input"
    )

    with pytest.raises(KeyError) as exc_b3:
        reg.resolve("")
    assert exc_b3.value.args[0] == "Unknown role taxonomy_key: ''", (
        "B3: empty-string input must raise with repr('') == \"''\""
    )

    with pytest.raises(KeyError) as exc_b4:
        reg.resolve("   ")
    assert exc_b4.value.args[0] == "Unknown role taxonomy_key: '   '", (
        "B4: whitespace-only input must surface the ORIGINAL unnormalized "
        "form in the error message (per f'{taxonomy_key!r}'), not the "
        "strip-to-empty form"
    )

    with pytest.raises(KeyError) as exc_b5:
        reg.resolve("unknown")
    assert "'unknown'" in str(exc_b5.value), (
        "B5: str(exc.value) substring match must still work for fo81-style "
        "consumers despite the KeyError quote-wrapping"
    )
    assert exc_b5.value.args[0] == "Unknown role taxonomy_key: 'unknown'", (
        "B5: args[0] exact match must also work on the same exception"
    )


def test_resolve_constructor_vs_factory_normalization_asymmetry_3_axis() -> None:
    uuid_x = _uuid()

    direct_reg = RoleRegistry({"BACKEND": uuid_x})
    with pytest.raises(KeyError):
        direct_reg.resolve("BACKEND")

    with pytest.raises(KeyError):
        direct_reg.resolve("backend")

    factory_reg = RoleRegistry.from_mapping({"BACKEND": uuid_x})
    assert factory_reg.resolve("BACKEND") == uuid_x, (
        "C3a: from_mapping must normalize dict keys so messy lookup succeeds"
    )
    assert factory_reg.resolve("backend") == uuid_x, (
        "C3b: from_mapping must normalize dict keys so clean lookup succeeds"
    )
    assert factory_reg.resolve("BACKEND") == factory_reg.resolve("backend"), (
        "C3c: messy and clean lookups must return the same UUID on a "
        "factory-built registry (symmetric on both sides)"
    )


def test_known_taxonomy_keys_frozenset_contract_3_axis() -> None:
    uuid_a = _uuid()
    uuid_b = _uuid()
    reg = RoleRegistry.from_mapping({"  Planner  ": uuid_a, "BACKEND": uuid_b})

    keys = reg.known_taxonomy_keys()
    assert isinstance(keys, frozenset), (
        "D1: known_taxonomy_keys must return a frozenset (existing tests "
        "only check content-equality which passes for set or frozenset)"
    )

    assert keys == frozenset({"planner", "backend"}), (
        "D2: known_taxonomy_keys must return the normalized lowercased + stripped keys post-factory"
    )

    with pytest.raises(AttributeError):
        keys.add("foo")  # type: ignore[attr-defined]
