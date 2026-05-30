"""HERMES_PREFLIGHT_LATENCY_SAMPLES`` Pattern B int fail-swallow-to-default."""


from __future__ import annotations

import pytest

from hermes_orchestrator.preflight import _latency_sample_count

_ENV_NAME = "HERMES_PREFLIGHT_LATENCY_SAMPLES"
_FLOOR = 1
_CEILING = 20
_DEFAULT = 1


def test_preflight_latency_samples_env_accept_arm_int_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #1 env-accept arm: bare ``int()`` + ``.strip()`` rescue + leading ``+``.

    Restricted to the **non-fail, non-clamp middle region** so each
    case exercises the canonical passthrough only. Floor / ceiling
    boundary values (``"1"`` / ``"20"``) sit in the loop as exact
    in-range passthrough -- the clamp branches at the same boundary
    values are pinned separately in Part B Blocks 4-5.

    The ``int-not-bool`` assertion catches a hypothetical refactor that
    returned ``bool(int(raw))`` or wrapped the result in ``BooleanInt``
    -- Python's ``bool`` is a subclass of ``int`` so a bare
    ``isinstance(result, int)`` check would silently pass.

    Pins 4 sub-contracts:

    1. **Canonical passthrough** -- ``int("5")`` returns ``5``.
    2. **Boundary passthrough** -- ``"1"`` / ``"20"`` survive without
       triggering the clamp (`max(1, 1) == 1`, `min(20, 20) == 20`).
    3. **Leading `+`** -- ``int("+5")`` succeeds.
    4. **`.strip()` rescue** -- whitespace-padded canonical accepted.
    """
    cases: list[tuple[str, str, int]] = [
        ("canon_1", "1", 1),
        ("canon_5", "5", 5),
        ("canon_10", "10", 10),
        ("canon_19", "19", 19),
        ("canon_20", "20", 20),
        ("leading_plus_5", "+5", 5),
        ("leading_plus_10", "+10", 10),
        ("ws_padded_5", "  5  ", 5),
        ("ws_tab_lf_10", "\t10\n", 10),
        ("ws_leading_19", " 19", 19),
        ("ws_trailing_20", "20 ", 20),
        ("ws_padded_plus_7", "  +7  ", 7),
    ]
    for _name, raw, expected in cases:
        monkeypatch.setenv(_ENV_NAME, raw)
        result = _latency_sample_count()
        assert result == expected, (
            f"accept raw={raw!r}: expected {expected}, got {result!r}"
        )
        assert isinstance(result, int) and not isinstance(result, bool), (
            f"accept raw={raw!r}: result type {type(result).__name__} "
            f"(should be int, not bool)"
        )


def test_preflight_latency_samples_env_clamp_lattice_and_path_convergence_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #1 ``[1, 20]`` clamp lattice + 3-path floor-convergence.

    The sharpest fo73 part: locks the ``[1, 20]`` clamping lattice AND
    the **three distinct paths to floor=1** in a single 5-block test
    so a refactor that:

    * removes ``or "1"`` (would change env-empty from ``1`` via
      short-circuit to ``1`` via ``int("")`` swallow -- functionally
      identical RESULT but path-distinct; Block 1 vs Block 2 catch).
    * removes ``except ValueError`` (would change env-whitespace-only /
      junk from ``1`` to a raised exception -- Blocks 2 / 3 catch).
    * removes ``max(n, 1)`` (would change env-``"0"`` / env-``"-5"``
      from ``1`` to ``0`` / ``-5`` -- Block 4 catches).
    * removes ``min(n, 20)`` (would change env-``"21"`` / env-``"9999"``
      from ``20`` to ``21`` / ``9999`` -- Block 5 catches).

    each fail with a per-block ``<path_label> raw=<raw>`` message
    identifying which path semantics changed.

    Pins 5 sub-contracts:

    * **Block 1 -- `or "1"` short-circuit path** (env-absent + env-empty).
    * **Block 2 -- `int("")` swallow path** (whitespace-only inputs
      bypass ``or "1"`` and reduce to empty after `.strip()`).
    * **Block 3 -- `int(<junk>)` swallow path** (junk + Pattern A
      truthy tokens; the latter pin ASYMMETRY vs fo65-70 where these
      enable a binary gate).
    * **Block 4 -- `max(n, 1)` floor-clamp path** (``"0"`` / negatives
      clamp UP to ``1``; KEY DIVERGENCE vs fo72's negative-passthrough).
    * **Block 5 -- `min(n, 20)` ceiling-clamp path** (``"21"`` and
      larger clamp DOWN to ``20``).
    """
    monkeypatch.delenv(_ENV_NAME, raising=False)
    result = _latency_sample_count()
    assert result == _FLOOR, (
        f"short_circuit env=delenv: expected {_FLOOR} via 'or \"1\"' "
        f"short-circuit, got {result!r}"
    )
    assert isinstance(result, int) and not isinstance(result, bool), (
        f"short_circuit env=delenv: result type {type(result).__name__}"
    )
    monkeypatch.setenv(_ENV_NAME, "")
    result = _latency_sample_count()
    assert result == _FLOOR, (
        f"short_circuit env='': expected {_FLOOR} via 'or \"1\"' "
        f"short-circuit, got {result!r}"
    )
    assert isinstance(result, int) and not isinstance(result, bool), (
        f"short_circuit env='': result type {type(result).__name__}"
    )

    empty_strip_cases: list[str] = ["   ", "\t\n", " ", "\t", "\n"]
    for raw in empty_strip_cases:
        monkeypatch.setenv(_ENV_NAME, raw)
        result = _latency_sample_count()
        assert result == _FLOOR, (
            f"empty_strip_swallow raw={raw!r}: expected {_FLOOR} via "
            f"int('') ValueError swallow, got {result!r}"
        )
        assert isinstance(result, int) and not isinstance(result, bool), (
            f"empty_strip_swallow raw={raw!r}: result type "
            f"{type(result).__name__}"
        )

    junk_cases: list[str] = ["abc", "true", "yes", "on", "TRUE", "NO"]
    for raw in junk_cases:
        monkeypatch.setenv(_ENV_NAME, raw)
        result = _latency_sample_count()
        assert result == _FLOOR, (
            f"junk_swallow raw={raw!r}: expected {_FLOOR} via "
            f"int(<junk>) ValueError swallow, got {result!r}"
        )
        assert isinstance(result, int) and not isinstance(result, bool), (
            f"junk_swallow raw={raw!r}: result type {type(result).__name__}"
        )

    floor_cases: list[str] = ["0", "-1", "-5", "-9999"]
    for raw in floor_cases:
        monkeypatch.setenv(_ENV_NAME, raw)
        result = _latency_sample_count()
        assert result == _FLOOR, (
            f"floor_clamp raw={raw!r}: expected {_FLOOR} via "
            f"max(n, 1) arithmetic clamp, got {result!r}"
        )
        assert isinstance(result, int) and not isinstance(result, bool), (
            f"floor_clamp raw={raw!r}: result type {type(result).__name__}"
        )

    ceiling_cases: list[str] = ["21", "100", "9999", "99999999"]
    for raw in ceiling_cases:
        monkeypatch.setenv(_ENV_NAME, raw)
        result = _latency_sample_count()
        assert result == _CEILING, (
            f"ceiling_clamp raw={raw!r}: expected {_CEILING} via "
            f"min(n, 20) arithmetic clamp, got {result!r}"
        )
        assert isinstance(result, int) and not isinstance(result, bool), (
            f"ceiling_clamp raw={raw!r}: result type {type(result).__name__}"
        )


def test_preflight_latency_samples_env_fail_swallow_string_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #1 fail-swallow-to-default -- STRUCTURAL TRIPLE INVERSION vs fo71/fo72.

    Asserts three independent properties per case rather than the
    single equality / single ``pytest.raises`` pattern from prior
    Pattern B Part C tests:

    1. **Does NOT raise** (vs fo72 Part C's ``pytest.raises(ValueError)``)
       -- a refactor that removes ``except ValueError`` surfaces as a
       ``ValueError`` raised from the bare ``_latency_sample_count()``
       call, which pytest reports on the assignment line with the
       offending env scalar visible in locals.
    2. **Returns exactly ``_DEFAULT == 1``** (vs fo71 Part C's
       ``== pytest.approx(0.1)`` layered fallthrough) -- a refactor
       that changes the default from ``1`` to any other constant
       surfaces per case.
    3. **Always returns a value in ``[_FLOOR, _CEILING]``** -- a
       refactor that bypasses the final ``min(max(n, 1), 20)`` clamp
       (e.g. moves it inside the try block) surfaces per case.

    Plus the ``int-not-bool`` type assertion per case catches a
    refactor that wraps the result in ``bool()`` or changes the return
    type to ``float`` via ``float(raw)`` substitution.

    Pins 5 sub-contracts in one matrix:

    1. **Junk -> swallow to default** -- bare ``int("abc")`` raises and
       is caught.
    2. **Pattern A truthy-token asymmetry** -- ``"true"`` / ``"yes"`` /
       ``"on"`` / ``"TRUE"`` all ``int()``-reject, mirroring fo72
       Part C's analogous asymmetry but **swallow-to-default** rather
       than **raise**. Catches "unify all envs to treat truthy tokens
       as 1" refactors that would silently change semantics.
    3. **Float strings reject** -- ``int("5.5")`` raises. KEY DIVERGENCE
       vs fo71 where ``float("5.5")`` accepts. A refactor swapping
       ``int()`` for ``float()`` would silently flip these cases from
       fail-swallow-to-1 to passthrough-5 (after `int()` cast) or
       passthrough-5.5 (typed wrong). Either way the equality check
       fails.
    4. **Scientific notation rejects** -- ``int("1e2")`` raises. Same
       swap-``int()``-for-``float()`` refactor catch.
    5. **Near-miss numeric** -- ``int("5x")`` / ``int("--5")`` /
       ``int("5,10")`` raise.
    """
    cases: list[tuple[str, str]] = [
        ("junk_abc", "abc"),
        ("junk_maybe", "maybe"),
        ("pattern_a_true", "true"),
        ("pattern_a_yes", "yes"),
        ("pattern_a_on", "on"),
        ("pattern_a_upper_true", "TRUE"),
        ("float_decimal", "5.5"),
        ("float_small", "0.5"),
        ("sci_lower_e", "1e2"),
        ("near_miss_trailing_x", "5x"),
        ("near_miss_double_neg", "--5"),
        ("near_miss_csv", "5,10"),
    ]
    for _name, raw in cases:
        monkeypatch.setenv(_ENV_NAME, raw)
        result = _latency_sample_count()
        assert result == _DEFAULT, (
            f"fail_swallow raw={raw!r}: expected default {_DEFAULT}, "
            f"got {result!r}"
        )
        assert _FLOOR <= result <= _CEILING, (
            f"fail_swallow raw={raw!r}: result {result!r} outside "
            f"[{_FLOOR}, {_CEILING}] clamp lattice"
        )
        assert isinstance(result, int) and not isinstance(result, bool), (
            f"fail_swallow raw={raw!r}: result type "
            f"{type(result).__name__} (should be int, not bool/float)"
        )
