"""NIMBUSWARE_DEADLOCK_ESCALATION_MINUTES`` env-layer Pattern B int + fail-RAISE."""

from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_orchestrator.anti_deadlock import load_anti_deadlock_settings

_ENV_NAME = "NIMBUSWARE_DEADLOCK_ESCALATION_MINUTES"


def _write_policy(
    tmp_path: Path,
    *,
    enabled: bool,
    min_progress: int,
    deadlock_minutes: int | float | str | None,
) -> None:
    """Write ``configs/escalation/policy.yaml`` under ``tmp_path``.

    ``deadlock_minutes`` accepts:

    * ``int`` / ``float`` -- written verbatim (PyYAML resolves to
      int / float).
    * ``"__null__"`` -- sentinel writing ``key: null`` so
      ``raw.get(key, 0)`` returns ``None`` and the downstream
      ``int(None)`` raises ``TypeError`` (Block 4 / 6 of Part B).
    * other ``str`` -- written as a quoted YAML string so PyYAML does
      NOT bool-resolve (Block 5: ``"abc"`` stays a string for
      ``int("abc")`` to raise ``ValueError``).
    * ``None`` -- omits the key entirely so ``raw.get(..., 0)`` returns
      the factory ``0`` (Block 3 of Part B).

    ``mkdir(parents=True, exist_ok=True)`` lets Part B re-write the
    same file across blocks within a single ``tmp_path`` test.
    """
    pol_dir = tmp_path / "configs" / "escalation"
    pol_dir.mkdir(parents=True, exist_ok=True)
    if deadlock_minutes is None:
        deadlock_line = ""
    elif deadlock_minutes == "__null__":
        deadlock_line = "deadlock_escalation_after_minutes: null\n"
    elif isinstance(deadlock_minutes, str):
        deadlock_line = f'deadlock_escalation_after_minutes: "{deadlock_minutes}"\n'
    else:
        deadlock_line = f"deadlock_escalation_after_minutes: {deadlock_minutes}\n"
    body = (
        "version: 1\n"
        f"{deadlock_line}"
        "anti_deadlock:\n"
        f"  enabled: {'true' if enabled else 'false'}\n"
        f"  min_progress_events: {min_progress}\n"
    )
    (pol_dir / "policy.yaml").write_text(body, encoding="utf-8")


def test_deadlock_minutes_env_accept_arm_int_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #19 env-accept arm: bare ``int()`` + NO clamping + ``.strip()`` rescue.

    YAML sentinel ``deadlock_escalation_after_minutes: 30`` so a refactor
    that accidentally falls through to YAML would surface as ``30``
    rather than the env value -- per-case tuple equality fails with a
    clear message identifying the offending env scalar.

    ``enabled=True`` and ``min_progress_events=7`` are orthogonal
    sentinels so a refactor that bled the env-layer into adjacent tuple
    positions would surface there.

    Pins 5 sub-contracts simultaneously:

    1. **Canonical passthrough** -- ``int("60")`` returns ``60``.
    2. **Zero boundary** -- ``"0"`` returns ``0`` literally; downstream
       ``should_emit_anti_deadlock_escalation`` short-circuits on
       ``stall_minutes <= 0`` separately in
       [anti_deadlock.py](packages\\nimbusware_orchestrator\\anti_deadlock.py)
       (line 68) but the LOAD function returns 0 verbatim.
    3. **NO clamping** -- negatives and large positives pass through
       (KEY DIVERGENCE from fo71 which clamps to ``[0.0, 1.0]``). A
       refactor adding ``max(0, n)`` would silently flip ``"-5"`` from
       -5 to 0 -- Part A catches it via two negative variants.
    4. **Leading `+`** -- ``int("+5")`` succeeds.
    5. **`.strip()` rescue** -- whitespace-padded canonical rescued,
       consistent with fo71.
    """
    _write_policy(tmp_path, enabled=True, min_progress=7, deadlock_minutes=30)
    cases: list[tuple[str, str, int]] = [
        ("canon_60", "60", 60),
        ("canon_5", "5", 5),
        ("zero", "0", 0),
        ("neg_small", "-5", -5),
        ("neg_large", "-9999", -9999),
        ("large", "9999", 9999),
        ("leading_plus", "+5", 5),
        ("ws_padded_60", "  60  ", 60),
        ("ws_tab_lf", "\t30\n", 30),
        ("ws_leading", " 5", 5),
        ("ws_trailing", "5 ", 5),
    ]
    for _name, raw, expected in cases:
        monkeypatch.setenv(_ENV_NAME, raw)
        result = load_anti_deadlock_settings(tmp_path)
        assert result == (True, expected, 7), (
            f"accept raw={raw!r}: expected (True, {expected}, 7), got {result!r}"
        )


def test_deadlock_minutes_env_two_layer_precedence_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #19 two-layer precedence cascade + YAML-side bare-``int()`` raise.

    Distinct from fo71 Part B (6-arm 3-layer cascade with
    ``except ValueError: pass``): fo72 Part B has **6 blocks across 2
    layers** with three "happy path" arms (1/2/3) + three "fail-RAISE
    propagation" arms (4/5) + one precedence-ordering proof (6).

    Pins 6 sub-contracts:

    * **Block 1** -- env-valid beats yaml -- standard precedence proof.
    * **Block 2** -- env-empty (``.strip()``-reduced non-empty check
      fails) -> yaml wins.
    * **Block 3** -- env-empty + key-absent -> factory ``0`` via
      ``raw.get(..., 0)``.
    * **Block 4** -- env-empty + yaml-null -> ``TypeError`` propagates
      via bare ``int(None)``. **KEY DIVERGENCE** vs fo71 whose
      ``parse_integrator_gate_min_score_to_pass`` catches and cascades.
    * **Block 5** -- env-empty + yaml-string-invalid -> ``ValueError``
      propagates via bare ``int("abc")``. Companion to Block 4.
    * **Block 6** -- env-valid + yaml-null -> env wins WITHOUT
      triggering yaml-null read; pins precedence ordering.
    """
    _write_policy(tmp_path, enabled=True, min_progress=7, deadlock_minutes=30)
    monkeypatch.setenv(_ENV_NAME, "60")
    result = load_anti_deadlock_settings(tmp_path)
    assert result == (True, 60, 7), (
        f"block_1_env_valid_with_yaml: expected (True, 60, 7), got {result!r}"
    )

    monkeypatch.delenv(_ENV_NAME, raising=False)
    result = load_anti_deadlock_settings(tmp_path)
    assert result == (True, 30, 7), (
        f"block_2_env_empty_with_yaml: expected (True, 30, 7), got {result!r}"
    )

    _write_policy(
        tmp_path,
        enabled=True,
        min_progress=7,
        deadlock_minutes=None,
    )
    result = load_anti_deadlock_settings(tmp_path)
    assert result == (True, 0, 7), (
        f"block_3_env_empty_no_yaml_key: expected (True, 0, 7) factory floor, got {result!r}"
    )

    _write_policy(
        tmp_path,
        enabled=True,
        min_progress=7,
        deadlock_minutes="__null__",
    )
    with pytest.raises(TypeError) as exc_info_null:
        load_anti_deadlock_settings(tmp_path)
    assert "int()" in str(exc_info_null.value) or "NoneType" in str(
        exc_info_null.value,
    ), (
        "block_4_env_empty_yaml_null: TypeError from int(None) should mention "
        f"int() or NoneType; got {str(exc_info_null.value)!r}"
    )

    _write_policy(
        tmp_path,
        enabled=True,
        min_progress=7,
        deadlock_minutes="abc",
    )
    with pytest.raises(ValueError) as exc_info_str:
        load_anti_deadlock_settings(tmp_path)
    assert "invalid literal for int()" in str(exc_info_str.value) or "abc" in str(
        exc_info_str.value,
    ), (
        "block_5_env_empty_yaml_string_invalid: ValueError from int('abc') should "
        f"mention 'invalid literal for int()' or the offending value; "
        f"got {str(exc_info_str.value)!r}"
    )

    _write_policy(
        tmp_path,
        enabled=True,
        min_progress=7,
        deadlock_minutes="__null__",
    )
    monkeypatch.setenv(_ENV_NAME, "60")
    result = load_anti_deadlock_settings(tmp_path)
    assert result == (True, 60, 7), (
        f"block_6_env_valid_with_yaml_null: expected (True, 60, 7) "
        f"(env short-circuits before yaml-null), got {result!r}"
    )


def test_deadlock_minutes_env_fail_raise_string_arm_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #19 fail-RAISE string-arm -- structural inversion vs fo71 Part C.

    YAML sentinel ``deadlock_escalation_after_minutes: 30`` so that IF
    a future "harmonize with fo71" refactor added
    ``try/except ValueError: pass`` and made fo72 cascade to YAML, the
    returned tuple would be ``(True, 30, 7)`` (same shape as Block 2 of
    Part B) -- the ``pytest.raises(ValueError)`` assertion would fail
    loudly with "DID NOT RAISE".

    Pins 5 sub-contracts:

    1. **Junk -> ValueError** -- bare ``int("abc")`` raises.
    2. **Pattern A truthy-token asymmetry** -- ``"true"`` / ``"yes"`` /
       ``"on"`` / ``"TRUE"`` all ``int()``-reject, mirroring fo71 Part C's
       analogous asymmetry but with **raise** rather than
       **fallthrough**. Catches "unify all envs to treat truthy tokens
       as 1" refactors.
    3. **Float strings reject** -- ``int("30.5")`` raises (strict int
       parser). KEY DIVERGENCE vs fo71 where ``float("30.5")`` accepts.
       A refactor swapping ``int()`` for ``float()`` would silently flip
       these cases from raise to value 30 -- Part C catches it.
    4. **Scientific notation rejects** -- ``int("1e2")`` raises. Same
       swap-``int()``-for-``float()`` refactor catch.
    5. **Near-miss numeric** -- ``int("30x")``, ``int("--30")``,
       ``int("30,60")`` raise; ``.strip()`` cannot rescue.

    The error-message substring check pins the **operator-visible
    diagnostic** so a refactor wrapping the raise in a custom exception
    with a misleading message surfaces as a test failure.
    """
    _write_policy(tmp_path, enabled=True, min_progress=7, deadlock_minutes=30)
    cases: list[tuple[str, str]] = [
        ("junk_abc", "abc"),
        ("junk_maybe", "maybe"),
        ("pattern_a_true", "true"),
        ("pattern_a_yes", "yes"),
        ("pattern_a_on", "on"),
        ("pattern_a_upper_true", "TRUE"),
        ("float_decimal", "30.5"),
        ("float_small", "0.5"),
        ("sci_lower_e", "1e2"),
        ("near_miss_trailing_x", "30x"),
        ("near_miss_double_neg", "--30"),
        ("near_miss_csv", "30,60"),
    ]
    for _name, raw in cases:
        monkeypatch.setenv(_ENV_NAME, raw)
        with pytest.raises(ValueError) as exc_info:
            load_anti_deadlock_settings(tmp_path)
        msg = str(exc_info.value)
        assert "invalid literal for int()" in msg or raw in msg, (
            f"fail_raise raw={raw!r}: ValueError message should mention "
            f"'invalid literal for int()' or the offending value; got {msg!r}"
        )
