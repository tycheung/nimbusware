"""RoleRegistry resolve + known_taxonomy_keys direct contracts."""


from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from hermes_orchestrator.registry import RoleRegistry


def _uuid() -> UUID:
    return uuid4()


def test_resolve_strip_lower_input_symmetry_5_axis() -> None:
    """Pin input normalization at registry.py:68 (k = key.strip().lower()).

    All axes build the registry via from_mapping with pre-normalized keys
    so the only variable is the input on the resolve() call side.

    A1 -- exact lowercase match returns correct UUID.
    A2 -- mixed-case input 'BackendWriter' resolves via .lower() arm.
    A3 -- whitespace-wrapped '  backendwriter  ' resolves via .strip() arm.
    A4 -- combined messy '\\t  BACKENDWRITER \\n' resolves via both chained.
    A5 -- multi-key registry returns the correct UUID per distinct key
    (proves dict lookup, not a singleton return).
    """
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
        "A5 precondition: the two test UUIDs must be distinct so the prior "
        "assertion is non-trivial"
    )


def test_resolve_keyerror_direct_message_contract_5_axis() -> None:
    """Pin KeyError raise + exact message at registry.py:69-71.

    Uses exc.value.args[0] for exact-message pinning (bypasses the
    str(KeyError(msg)) quote-wrapping quirk where str() returns "'msg'").

    B1 -- unknown key raises KeyError; args[0] is exact f-string output.
    B2 -- empty registry: any input raises KeyError.
    B3 -- empty-string '' input -> strip-to-empty -> KeyError with "''" repr.
    B4 -- whitespace-only '   ' input -> KeyError msg includes repr of
    ORIGINAL input (not the normalized form) per f"{taxonomy_key!r}".
    B5 -- dual access pattern: str(exc.value) substring match (fo81 style)
    AND args[0] exact match both succeed on the same exception.
    """
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
    """Pin the public-API footgun: __init__ does NOT normalize; factories do.

    The constructor is public (no underscore prefix) so direct calls are
    syntactically legal. This test pins the resulting behavioral asymmetry
    so any future "fix" to the constructor would visibly break the contract.

    C1 -- direct RoleRegistry({'BACKEND': uuid}) -> resolve('BACKEND') fails
    because resolve() lowercases input to 'backend' but dict still has 'BACKEND'.
    C2 -- same construction: resolve('backend') ALSO fails because the dict
    still has 'BACKEND' not 'backend' (no factory normalization happened).
    C3 -- from_mapping({'BACKEND': uuid}) normalizes during construction;
    resolve('BACKEND') AND resolve('backend') both succeed and return the
    same UUID, proving the factory is the safe construction path.
    """
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
    """Pin immutability + content contract at registry.py:74-75.

    D1 -- return type is frozenset (not just any set-like).
    D2 -- contents are the normalized keys after from_mapping.
    D3 -- returned frozenset is immutable at runtime (.add raises
    AttributeError because frozenset has no .add method).
    """
    uuid_a = _uuid()
    uuid_b = _uuid()
    reg = RoleRegistry.from_mapping({"  Planner  ": uuid_a, "BACKEND": uuid_b})

    keys = reg.known_taxonomy_keys()
    assert isinstance(keys, frozenset), (
        "D1: known_taxonomy_keys must return a frozenset (existing tests "
        "only check content-equality which passes for set or frozenset)"
    )

    assert keys == frozenset({"planner", "backend"}), (
        "D2: known_taxonomy_keys must return the normalized lowercased + "
        "stripped keys post-factory"
    )

    with pytest.raises(AttributeError):
        keys.add("foo")  # type: ignore[attr-defined]
