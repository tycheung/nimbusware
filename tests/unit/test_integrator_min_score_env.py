"""NIMBUSWARE_INTEGRATOR_MIN_SCORE_TO_PASS`` env-layer Pattern B + 3-layer precedence."""

from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_orchestrator.integrator_gate import (
    effective_integrator_min_score_to_pass,
)

_ENV_NAME = "NIMBUSWARE_INTEGRATOR_MIN_SCORE_TO_PASS"
_PROFILE = "ms"


def _write_workflow_min_score(tmp_path: Path, value: float | None) -> None:
    """Write ``configs/workflows/ms.yaml`` under ``tmp_path``.

    ``value`` is the ``integrator_gate.min_score_to_pass`` to embed.
    ``None`` writes the profile WITHOUT the key (only ``enabled: true``)
    so ``parse_integrator_gate_min_score_to_pass`` in
    [integrator_gate.py](packages\\nimbusware_orchestrator\\integrator_gate.py)
    returns ``None`` and the wf layer falls through to thresholds.yaml.

    ``mkdir(parents=True, exist_ok=True)`` permits multiple
    re-writes within a single ``tmp_path`` test (Part B rewrites
    workflow and thresholds across blocks).
    """
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    if value is None:
        body = "version: 1\nintegrator_gate:\n  enabled: true\n"
    else:
        body = f"version: 1\nintegrator_gate:\n  enabled: true\n  min_score_to_pass: {value}\n"
    (wf_dir / f"{_PROFILE}.yaml").write_text(body, encoding="utf-8")


def _write_thresholds(tmp_path: Path, value: float | None) -> None:
    """Write ``configs/integrator/thresholds.yaml`` under ``tmp_path``.

    ``value`` ``None`` writes the file WITHOUT ``min_score_to_pass``
    so ``load_integrator_min_score_from_thresholds`` in
    [integrator_gate.py](packages\\nimbusware_orchestrator\\integrator_gate.py)
    returns the ``raw.get(..., 0.0)`` factory default.
    """
    ig_dir = tmp_path / "configs" / "integrator"
    ig_dir.mkdir(parents=True, exist_ok=True)
    if value is None:
        body = "version: 1\nenabled: false\n"
    else:
        body = f"version: 1\nenabled: false\nmin_score_to_pass: {value}\n"
    (ig_dir / "thresholds.yaml").write_text(body, encoding="utf-8")


def test_integrator_min_score_env_accept_arm_numeric_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #13 env-accept arm: float coerce + ``[0.0, 1.0]`` clamp + ``.strip()`` rescue.

    Workflow YAML sentinel ``0.1`` and thresholds.yaml sentinel ``0.5``
    are written so that any fallthrough (env-gate rejected the variant)
    would surface as a wrong value rather than a silent pass --
    ``pytest.approx`` equality on each case identifies the offending
    env scalar.

    Pins 5 sub-contracts simultaneously:

    1. **Boundary passthrough** -- ``"0.0"`` / ``"1.0"`` not clamped to
       0/1 by ``max(0, min(1, v))`` (boundary inclusion).
    2. **In-range passthrough** -- arbitrary precision preserved.
    3. **Integer coercion** -- ``"1"`` becomes float ``1.0``.
    4. **Clamping** -- negative -> 0.0, over-1.0 -> 1.0.
    5. **`.strip()` rescue** -- ``"  0.5  "`` produces ``0.5`` (KEY
       DIVERGENCE from Pattern A fo65/66/67/68/69/70 envs that never
       call ``.strip()`` so whitespace-padded canonical fails-closed
       there). A future refactor dropping ``.strip()`` would silently
       flip the last two cases.
    """
    _write_workflow_min_score(tmp_path, 0.1)
    _write_thresholds(tmp_path, 0.5)
    cases: list[tuple[str, str, float]] = [
        ("boundary_zero", "0.0", 0.0),
        ("boundary_one", "1.0", 1.0),
        ("in_range_half", "0.5", 0.5),
        ("in_range_low", "0.123", 0.123),
        ("in_range_high", "0.999", 0.999),
        ("int_zero", "0", 0.0),
        ("int_one", "1", 1.0),
        ("clamp_neg_small", "-0.5", 0.0),
        ("clamp_neg_large", "-100.0", 0.0),
        ("clamp_neg_zero", "-0.0", 0.0),
        ("clamp_over_small", "1.5", 1.0),
        ("clamp_over_large", "100.0", 1.0),
        ("ws_padded_half", "  0.5  ", 0.5),
        ("ws_tab_lf_half", "\t0.7\n", 0.7),
    ]
    for _name, raw, expected in cases:
        monkeypatch.setenv(_ENV_NAME, raw)
        actual = effective_integrator_min_score_to_pass(tmp_path, _PROFILE)
        assert actual == pytest.approx(expected), (
            f"accept raw={raw!r}: expected {expected!r}, got {actual!r}"
        )


def test_integrator_min_score_env_three_layer_precedence_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #13 three-layer precedence cascade matrix.

    First slice in the env-layer sweep to lock a **3-layer cascade**:
    env > workflow YAML > thresholds.yaml > 0.0 factory floor.

    Distinct from fo69 Part B (three branches inside a single env-gate
    accept arm with asymmetric call-count signatures) and fo70 Part B
    (2x2 compound AND-gate): fo71 Part B is **6-arm 3-layer cascade**
    pinning precedence ordering AND fail-closed cascade simultaneously.

    Pins 6 sub-contracts:

    * **Block 1** -- env-valid beats wf and thresholds.
    * **Block 2** -- env-empty (non-empty check fails before
      ``float()``) -> wf wins.
    * **Block 3** -- env-empty + wf-missing-key (``parse_...`` returns
      ``None``) -> thresholds wins.
    * **Block 4** -- env-empty + wf-missing + thresholds-missing-key
      -> ``raw.get(..., 0.0)`` factory floor.
    * **Block 5** -- env-INVALID -> wf wins via the
      ``except ValueError: pass`` arm at
      [integrator_gate.py:162-163](packages\\nimbusware_orchestrator\\integrator_gate.py).
      A refactor narrowing or removing the ``except`` would surface
      ``ValueError`` to callers instead of degrading silently -- Block
      5 catches it.
    * **Block 6** -- env-INVALID + wf-missing -> thresholds wins via
      **double fallthrough**. A refactor short-circuiting on env-fail
      (e.g. returning ``0.0`` directly) would flip Block 6 from 0.5
      to 0.0.
    """
    _write_workflow_min_score(tmp_path, 0.1)
    _write_thresholds(tmp_path, 0.5)
    monkeypatch.setenv(_ENV_NAME, "0.99")
    actual = effective_integrator_min_score_to_pass(tmp_path, _PROFILE)
    assert actual == pytest.approx(0.99), (
        f"block_1_env_valid_with_wf_and_thresholds: expected 0.99, got {actual!r}"
    )

    monkeypatch.delenv(_ENV_NAME, raising=False)
    actual = effective_integrator_min_score_to_pass(tmp_path, _PROFILE)
    assert actual == pytest.approx(0.1), (
        f"block_2_env_empty_with_wf_and_thresholds: expected 0.1 (wf), got {actual!r}"
    )

    _write_workflow_min_score(tmp_path, None)
    actual = effective_integrator_min_score_to_pass(tmp_path, _PROFILE)
    assert actual == pytest.approx(0.5), (
        f"block_3_env_empty_no_wf_with_thresholds: expected 0.5 (thresholds), got {actual!r}"
    )

    _write_thresholds(tmp_path, None)
    actual = effective_integrator_min_score_to_pass(tmp_path, _PROFILE)
    assert actual == pytest.approx(0.0), (
        f"block_4_env_empty_no_wf_no_thresholds: expected 0.0 (factory floor), got {actual!r}"
    )

    _write_workflow_min_score(tmp_path, 0.1)
    _write_thresholds(tmp_path, 0.5)
    monkeypatch.setenv(_ENV_NAME, "abc")
    actual = effective_integrator_min_score_to_pass(tmp_path, _PROFILE)
    assert actual == pytest.approx(0.1), (
        f"block_5_env_invalid_with_wf: expected 0.1 (wf via fail-closed proof), got {actual!r}"
    )

    _write_workflow_min_score(tmp_path, None)
    actual = effective_integrator_min_score_to_pass(tmp_path, _PROFILE)
    assert actual == pytest.approx(0.5), (
        "block_6_env_invalid_no_wf_with_thresholds: expected 0.5 "
        f"(thresholds via double fallthrough), got {actual!r}"
    )


def test_integrator_min_score_env_fail_closed_string_arm_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #13 asymmetric env-layer fail-closed string-arm.

    Workflow YAML sentinel ``0.1`` so every fail-closed variant
    cascades there and the assertion ``== pytest.approx(0.1)`` proves
    the env-gate fell through. Parallel to fo65/66/67/68/69/70 Part C
    in structure but fundamentally different in content because:

    * Pattern A's whitespace-padded canonical (``"  1  "``) fails-closed
      there but is an **accept** case in fo71 Part A (``.strip()``
      rescue).
    * Pattern A's ``"on"`` is asymmetric vs YAML coercer; here it is
      asymmetric vs Pattern A itself (``float("on")`` raises).
    * Numeric near-miss is a new sub-contract pinning the strict
      ``float()`` parser.

    Pins 5 sub-contracts:

    1. **Empty / whitespace-only short-circuit** -- ``.strip()`` reduces
       to ``""``, ``if env_raw:`` non-empty check fails BEFORE ``float()``.
    2. **Pattern A truthy-token asymmetry** -- ``"true"`` / ``"yes"`` /
       ``"on"`` / ``"TRUE"`` are NOT numerically valid here. A future
       "unify all envs to treat truthy tokens as 1.0" refactor would
       silently flip these cases.
    3. **Junk strings** -- generic ``ValueError`` fallthrough.
    4. **Near-miss numeric** -- ``float()`` is strict. ``"0.5x"`` /
       ``"0.5.6"`` / ``"--0.5"`` / ``"0.5 abc"`` / ``"0.5,0.6"`` all
       raise. A refactor swapping for a permissive parser would
       silently flip near-misses.
    5. **`.strip()` cannot rescue interior content** -- ``"0.5 abc"``
       strips to ``"0.5 abc"`` (no leading/trailing whitespace) which
       ``float()``-rejects. Distinct from Part A's rescue case.
    """
    _write_workflow_min_score(tmp_path, 0.1)
    _write_thresholds(tmp_path, 0.5)
    cases: list[tuple[str, str]] = [
        ("empty", ""),
        ("ws_only_spaces", "   "),
        ("ws_only_tab_lf", "\t\n"),
        ("pattern_a_one_word", "true"),
        ("pattern_a_yes", "yes"),
        ("pattern_a_on", "on"),
        ("pattern_a_upper_true", "TRUE"),
        ("junk_abc", "abc"),
        ("junk_maybe", "maybe"),
        ("near_miss_trailing_x", "0.5x"),
        ("near_miss_double_dot", "0.5.6"),
        ("near_miss_double_neg", "--0.5"),
        ("near_miss_trailing_word", "0.5 abc"),
        ("near_miss_csv", "0.5,0.6"),
    ]
    for _name, raw in cases:
        monkeypatch.setenv(_ENV_NAME, raw)
        actual = effective_integrator_min_score_to_pass(tmp_path, _PROFILE)
        assert actual == pytest.approx(0.1), (
            f"fail_closed raw={raw!r}: env should fall through to wf=0.1, got {actual!r}"
        )
