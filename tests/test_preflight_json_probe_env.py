"""HERMES_PREFLIGHT_JSON_PROBE`` env-layer string-arm contract."""


from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from hermes_orchestrator.preflight import run_model_preflight

_PRIMARY_MODEL_ID = "dev:primary"
_FALLBACK_MODEL_IDS: list[str] = ["dev:fallback"]
_OLLAMA_TAGS_RESPONSE: dict[str, Any] = {"models": [{"name": _PRIMARY_MODEL_ID}]}

_OLLAMA_POST_RESPONSE: dict[str, Any] = {
    "model_info": {"context_length": 8192},
    "message": {"content": '{"ok":true}'},
}


def _mock_response(json_data: dict[str, Any]) -> MagicMock:
    """Build a ``httpx.Response``-shaped MagicMock returning ``json_data``."""
    resp = MagicMock(spec=httpx.Response)
    resp.raise_for_status.return_value = None
    resp.json.return_value = json_data
    return resp


def _call_preflight() -> tuple[str, dict[str, Any], bool]:
    """Invoke ``run_model_preflight`` with the shared test fixture."""
    return run_model_preflight(
        base_url="http://invalid.test",
        health_path="/api/tags",
        primary_model_id=_PRIMARY_MODEL_ID,
        fallback_model_ids=_FALLBACK_MODEL_IDS,
    )


@contextmanager
def _mocked_httpx(*, probe_fails: bool = False) -> Iterator[None]:
    """Patch ``httpx.get`` + ``httpx.post`` so preflight reaches the probe gate.

    ``/api/tags`` (the health probe) always returns ``_OLLAMA_TAGS_RESPONSE``.
    ``/api/show`` (called by ``_ollama_context_length``) always returns the
    unified ``_OLLAMA_POST_RESPONSE`` (the ``"model_info"`` key is what that
    function consumes).

    ``/api/chat`` (called by ``_optional_json_probe`` only when the env-gate
    accepts) raises ``httpx.HTTPError`` when ``probe_fails=True`` -- the probe's
    ``except (httpx.HTTPError, ValueError, TypeError, json.JSONDecodeError)``
    arm converts that to ``(False, lat, str(exc))``, exercising the FAIL arm.
    """

    def post_side_effect(url: str, **_kwargs: Any) -> MagicMock:
        if probe_fails and "/api/chat" in url:
            raise httpx.HTTPError("simulated probe failure")
        return _mock_response(_OLLAMA_POST_RESPONSE)

    with patch(
        "hermes_orchestrator.preflight.httpx.get",
        return_value=_mock_response(_OLLAMA_TAGS_RESPONSE),
    ), patch(
        "hermes_orchestrator.preflight.httpx.post",
        side_effect=post_side_effect,
    ):
        yield


def test_preflight_json_probe_env_force_on_string_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #1 ``HERMES_PREFLIGHT_JSON_PROBE`` force-on truthy tuple membership.

    The env-gate at [preflight.py:194](d:\\Hermes\\packages\\hermes_orchestrator\\preflight.py)
    uses ``in ("1", "true", "yes")``. Truthy variants reach
    ``_optional_json_probe`` which, with ``_mocked_httpx`` returning the
    canonical OK response for ``/api/chat``, succeeds and adds two
    observable markers to ``evidence``:

    * ``json_probe_latency_ms`` (always present when env-gate accepts)
    * ``"structured_json_probe_ok"`` in ``evidence["checks_passed"]``

    If the env-gate had rejected the variant, neither key would surface
    and the assertions fail with a clear per-case message identifying
    the offending env scalar.
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
        monkeypatch.delenv("HERMES_SKIP_PREFLIGHT", raising=False)
        monkeypatch.setenv("HERMES_PREFLIGHT_JSON_PROBE", raw)
        with _mocked_httpx(probe_fails=False):
            _selected, evidence, _used_primary = _call_preflight()
        assert "json_probe_latency_ms" in evidence, (
            f"force_on raw={raw!r}: json_probe_latency_ms missing"
        )
        assert "structured_json_probe_ok" in evidence["checks_passed"], (
            f"force_on raw={raw!r}: structured_json_probe_ok missing"
        )


def test_preflight_json_probe_env_probe_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #1 two-arm contract within the env-gate-accept branch.

    Distinct from fo65 / 66 / 67 Part B (which all locked a single-tuple
    shape) -- this slice's env has **two** observable downstream arms
    within the accept branch:

    * **OK arm**: ``_optional_json_probe`` returns ``(True, lat, None)`` ->
      ``json_probe_latency_ms`` present, ``json_probe_error`` ABSENT,
      ``"structured_json_probe_ok"`` in ``checks_passed``,
      ``"structured_json_probe_skipped_or_failed"`` ABSENT.
    * **FAIL arm**: ``_optional_json_probe`` returns ``(False, lat,
      "<err>")`` -> ``json_probe_latency_ms`` present, ``json_probe_error``
      present (and a ``str``), ``"structured_json_probe_skipped_or_failed"``
      in ``checks_passed``, ``"structured_json_probe_ok"`` ABSENT.

    A refactor that drops ``json_probe_latency_ms`` on the FAIL path,
    leaks ``"structured_json_probe_ok"`` into FAIL (or vice versa), or
    changes ``json_probe_error`` from ``str`` to e.g. an exception object
    breaks operator-facing evidence -- per-arm messages catch each
    independently.
    """
    monkeypatch.delenv("HERMES_SKIP_PREFLIGHT", raising=False)
    monkeypatch.setenv("HERMES_PREFLIGHT_JSON_PROBE", "1")

    with _mocked_httpx(probe_fails=False):
        _selected, ok_evidence, _used_primary = _call_preflight()
    assert "json_probe_latency_ms" in ok_evidence, (
        "ok_arm: json_probe_latency_ms missing"
    )
    assert "json_probe_error" not in ok_evidence, (
        "ok_arm: json_probe_error unexpectedly present"
    )
    ok_checks = ok_evidence["checks_passed"]
    assert "structured_json_probe_ok" in ok_checks, (
        "ok_arm: structured_json_probe_ok missing"
    )
    assert "structured_json_probe_skipped_or_failed" not in ok_checks, (
        "ok_arm: structured_json_probe_skipped_or_failed leaked"
    )

    with _mocked_httpx(probe_fails=True):
        _selected, fail_evidence, _used_primary = _call_preflight()
    assert "json_probe_latency_ms" in fail_evidence, (
        "fail_arm: json_probe_latency_ms missing"
    )
    assert "json_probe_error" in fail_evidence, (
        "fail_arm: json_probe_error missing"
    )
    assert isinstance(fail_evidence["json_probe_error"], str), (
        f"fail_arm: json_probe_error wrong type "
        f"(got {type(fail_evidence['json_probe_error']).__name__})"
    )
    fail_checks = fail_evidence["checks_passed"]
    assert "structured_json_probe_skipped_or_failed" in fail_checks, (
        "fail_arm: structured_json_probe_skipped_or_failed missing"
    )
    assert "structured_json_probe_ok" not in fail_checks, (
        "fail_arm: structured_json_probe_ok leaked"
    )


def test_preflight_json_probe_env_fail_closed_string_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #1 asymmetric fail-closed string-arm at the env gate.

    Loops 12 fail-closed variants spanning four sub-contracts (parallel
    to fo65 / 66 / 67 Part C):

    1. **Env-absent** -- the production default when the env is unset
       skips the probe block entirely.
    2. **No ``.strip()``** -- whitespace-padded canonical fail-closed
       because ``.lower()`` alone does not trim whitespace. A future
       refactor adding ``.strip()`` to "match the YAML coercer" silently
       flips ``" 1 "`` from "probe skipped" to "probe runs" -- this
       test fails loudly on exactly that change.
    3. **``"on"`` / ``"off"`` asymmetry** vs YAML coercer -- the env
       layer excludes ``"on"`` from the truthy tuple even though the
       workflow YAML coercer accepts it.
    4. **Single-tuple membership** -- case-folded falsy (``"FALSE"`` /
       ``"NO"``) and unknown tokens both fail-closed via the same ``in``
       predicate, plus empty / junk / near-miss / interior whitespace.

    httpx is mocked successfully (so preflight reaches line 194 cleanly)
    but the env-gate rejects, so **none** of the four probe-related
    keys / entries should surface in the returned evidence.
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
        monkeypatch.delenv("HERMES_SKIP_PREFLIGHT", raising=False)
        if raw is None:
            monkeypatch.delenv("HERMES_PREFLIGHT_JSON_PROBE", raising=False)
        else:
            monkeypatch.setenv("HERMES_PREFLIGHT_JSON_PROBE", raw)
        with _mocked_httpx(probe_fails=False):
            _selected, evidence, _used_primary = _call_preflight()
        assert "json_probe_latency_ms" not in evidence, (
            f"fail_closed raw={raw!r}: json_probe_latency_ms leaked"
        )
        assert "json_probe_error" not in evidence, (
            f"fail_closed raw={raw!r}: json_probe_error leaked"
        )
        checks = evidence["checks_passed"]
        assert "structured_json_probe_ok" not in checks, (
            f"fail_closed raw={raw!r}: structured_json_probe_ok leaked"
        )
        assert "structured_json_probe_skipped_or_failed" not in checks, (
            f"fail_closed raw={raw!r}: "
            "structured_json_probe_skipped_or_failed leaked"
        )
