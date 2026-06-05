from __future__ import annotations

from typing import Any
from unittest.mock import patch

import httpx
import pytest

from nimbusware_orchestrator.preflight import PreflightError, run_model_preflight

_PRIMARY_MODEL_ID = "dev:primary"
_FALLBACK_MODEL_IDS: list[str] = ["dev:fallback"]

_SKIPPED_EVIDENCE: dict[str, Any] = {
    "skipped": True,
    "reason": "NIMBUSWARE_SKIP_PREFLIGHT",
    "checks_passed": ["skipped"],
    "context_tokens": 8192,
    "p95_latency_ms": 0,
    "health_latency_ms": 0,
}
_SKIPPED_TUPLE: tuple[str, dict[str, Any], bool] = (
    _PRIMARY_MODEL_ID,
    _SKIPPED_EVIDENCE,
    True,
)


def _call_preflight() -> tuple[str, dict[str, Any], bool]:
    """Invoke ``run_model_preflight`` with the shared test fixture.

    All three parts share the same call shape so the only varying input
    is ``NIMBUSWARE_SKIP_PREFLIGHT``. ``base_url="http://invalid.test"`` is
    deliberately unreachable so any fall-through (Parts A / B) would
    raise ``PreflightError`` and surface immediately on the assertion
    line if the env-gate misbehaved.
    """
    return run_model_preflight(
        base_url="http://invalid.test",
        health_path="/api/tags",
        primary_model_id=_PRIMARY_MODEL_ID,
        fallback_model_ids=_FALLBACK_MODEL_IDS,
    )


def test_skip_preflight_env_force_on_string_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #1 ``NIMBUSWARE_SKIP_PREFLIGHT`` force-on truthy tuple membership.

    The env-gate at [preflight.py:115](packages\\nimbusware_orchestrator\\preflight.py)
    uses ``in ("1", "true", "yes")`` so truthy variants short-circuit
    BEFORE any ``httpx.get`` call. No network mocking is needed -- if
    the env-gate had rejected a variant, the test would fall through to
    ``httpx.get("http://invalid.test/api/tags", ...)`` which raises
    ``httpx.ConnectError`` -> caught and re-raised as ``PreflightError``,
    surfacing as an uncaught exception on the assertion line with a
    per-case message.
    """
    cases: list[tuple[str, str]] = [
        ("canon_one", "1"),
        ("canon_true", "true"),
        ("canon_yes", "yes"),
        ("upper_true", "TRUE"),
        ("title_true", "True"),
        ("upper_yes", "YES"),
        ("title_yes", "Yes"),
        ("mixed_true", "trUE"),
        ("mixed_yes", "yEs"),
    ]
    for _name, raw in cases:
        monkeypatch.setenv("NIMBUSWARE_SKIP_PREFLIGHT", raw)
        result = _call_preflight()
        assert result == _SKIPPED_TUPLE, f"force_on raw={raw!r}"


def test_skip_preflight_env_skipped_tuple_shape_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #1 exact ``(str, dict, bool)`` skipped-tuple shape and types.

    Part A's ``result == _SKIPPED_TUPLE`` quietly accepts type-coerced
    refactors: ``True == 1`` is ``True`` in Python, so changing
    ``"skipped": True`` to ``"skipped": 1`` (or ``used_primary=True`` to
    ``used_primary=1``) would silently pass Part A. This test runs
    per-key / per-element checks using ``type(actual) is type(expected)``
    plus value equality to catch that drift, plus an explicit
    ``set(evidence.keys()) == documented_keys`` check to catch
    added / removed dict entries.

    Loops only 4 canonical truthy cases (the variants matter for Part A;
    the **shape** is invariant across them).
    """
    cases: list[tuple[str, str]] = [
        ("canon_one", "1"),
        ("canon_true", "true"),
        ("canon_yes", "yes"),
        ("title_true", "True"),
    ]
    expected_keys = set(_SKIPPED_EVIDENCE.keys())
    for _name, raw in cases:
        monkeypatch.setenv("NIMBUSWARE_SKIP_PREFLIGHT", raw)
        result = _call_preflight()
        assert isinstance(result, tuple) and len(result) == 3, (
            f"shape raw={raw!r}: outer tuple arity"
        )
        selected, evidence, used_primary = result
        assert type(selected) is str and selected == _PRIMARY_MODEL_ID, (
            f"shape raw={raw!r}: selected_model_id"
        )
        assert type(used_primary) is bool and used_primary is True, (
            f"shape raw={raw!r}: used_primary"
        )
        assert isinstance(evidence, dict), f"shape raw={raw!r}: evidence is dict"
        assert set(evidence.keys()) == expected_keys, f"shape raw={raw!r}: evidence keys"
        for key, expected in _SKIPPED_EVIDENCE.items():
            actual = evidence[key]
            assert type(actual) is type(expected), (
                f"shape raw={raw!r}: evidence[{key!r}] type "
                f"(expected {type(expected).__name__}, got "
                f"{type(actual).__name__})"
            )
            assert actual == expected, (
                f"shape raw={raw!r}: evidence[{key!r}] value "
                f"(expected {expected!r}, got {actual!r})"
            )


def test_skip_preflight_env_fail_closed_string_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #1 asymmetric fail-closed string-arm at the env gate.

    Loops 12 fail-closed variants spanning four sub-contracts (parallel
    to follow-on 65 / 66 Part C):

    1. **Env-absent** -- the production default when the env is unset
       falls through to ``httpx.get``.
    2. **No ``.strip()``** -- whitespace-padded canonical (``"  1  "``
       / ``" true "`` / ``"\\tyes\\n"``) fail-closed because ``.lower()``
       alone does not trim whitespace. A future refactor adding
       ``.strip()`` to "match the YAML coercer" silently flips
       ``" 1 "`` from "preflight runs" to "preflight skipped" -- this
       test fails loudly on exactly that change.
    3. **``"on"`` / ``"off"`` asymmetry** vs YAML coercer -- the env
       layer excludes ``"on"`` from the truthy tuple even though the
       workflow YAML coercer accepts it (parallel to fo51 / fo62 /
       fo63 / fo64 / fo65 / fo66).
    4. **Single-tuple membership** -- case-folded falsy (``"FALSE"`` /
       ``"NO"``) and unknown tokens both fail-closed via the same
       ``in`` predicate (no separate falsy tuple to short-circuit
       through), plus empty / junk / near-miss / interior whitespace.

    ``httpx.get`` is patched at the module boundary to raise
    ``httpx.ConnectError``; the function's ``except (httpx.HTTPError,
    ValueError)`` arm converts that to
    ``PreflightError("runtime not reachable: ...")``. Reaching that
    exception proves the env-gate did NOT short-circuit -- otherwise
    the skipped 3-tuple would be returned without ever calling
    ``httpx.get``.
    """
    cases: list[tuple[str, str | None]] = [
        ("env_absent", None),
        ("ws_one_pad", "  1  "),
        ("ws_true_pad", " true "),
        ("ws_tab_yes_lf", "\tyes\n"),
        ("yaml_on_lower", "on"),
        ("yaml_on_upper", "ON"),
        ("upper_false", "FALSE"),
        ("upper_no", "NO"),
        ("empty", ""),
        ("junk_maybe", "maybe"),
        ("near_miss_true_bang", "true!"),
        ("interior_ws", " ye s "),
    ]
    for _name, raw in cases:
        if raw is None:
            monkeypatch.delenv("NIMBUSWARE_SKIP_PREFLIGHT", raising=False)
        else:
            monkeypatch.setenv("NIMBUSWARE_SKIP_PREFLIGHT", raw)
        with patch(
            "nimbusware_orchestrator.preflight.httpx.get",
            side_effect=httpx.ConnectError("connection refused"),
        ):
            try:
                _call_preflight()
            except PreflightError as exc:
                assert "runtime not reachable" in str(exc), (
                    f"fail_closed raw={raw!r}: wrong message: {exc!s}"
                )
            else:
                pytest.fail(f"fail_closed raw={raw!r} did not raise PreflightError")
