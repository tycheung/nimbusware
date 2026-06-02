"""HERMES_USE_LLM`` env-layer string-arm contract."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from hermes_orchestrator.pipeline import RunOrchestrator, make_dev_orchestrator

_MODEL_ID = "dev:primary"


@contextmanager
def _patched_execute(
    orch: RunOrchestrator,
    *,
    model_id: str | None = _MODEL_ID,
    llm_raises: bool = False,
) -> Iterator[tuple[MagicMock, MagicMock]]:
    """Patch the three injection points around ``execute_plan_stage``.

    Yields ``(mock_llm, mock_stub)`` so call counts are inspectable.

    ``model_id``: controls ``_selected_model_for_run``'s return; ``None``
    exercises Part B's no-model fallback.

    ``llm_raises``: when True, the patched LLM raises ``Exception("simulated
    llm failure")`` so the ``except Exception: pass`` arm at
    [pipeline.py:696](d:\\Hermes\\packages\\hermes_orchestrator\\pipeline.py)
    swallows it and the stub fallback fires (Part B's LLM-raises branch).
    """
    llm_kwargs: dict[str, Any] = (
        {"side_effect": Exception("simulated llm failure")} if llm_raises else {}
    )
    with (
        patch.object(orch, "_selected_model_for_run", return_value=model_id),
        patch("hermes_orchestrator.pipeline.execute_plan_stage_llm", **llm_kwargs) as mock_llm,
        patch(
            "hermes_orchestrator.pipeline.emit_stub_plan_stage",
        ) as mock_stub,
    ):
        yield mock_llm, mock_stub


def test_use_llm_env_force_on_string_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #16 ``HERMES_USE_LLM`` force-on truthy tuple membership.

    The env-gate at [pipeline.py:679](d:\\Hermes\\packages\\hermes_orchestrator\\pipeline.py)
    uses ``in ("1", "true", "yes")``. With ``_selected_model_for_run``
    returning a valid model and the LLM mock returning normally, truthy
    variants must reach the LLM-ok branch where ``execute_plan_stage_llm``
    is invoked once and ``emit_stub_plan_stage`` is suppressed by the
    ``return`` at line 695.

    If the env-gate had rejected the variant, ``mock_llm.call_count``
    would be 0 and ``mock_stub.call_count`` would be 1, failing both
    assertions with a clear per-case message identifying the offending
    env scalar.
    """
    orch, _store = make_dev_orchestrator()
    rid = orch.create_run("default")
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
        monkeypatch.setenv("HERMES_USE_LLM", raw)
        with _patched_execute(orch) as (mock_llm, mock_stub):
            orch.execute_plan_stage(rid)
        assert mock_llm.call_count == 1, (
            f"force_on raw={raw!r}: LLM call count (expected 1, got {mock_llm.call_count})"
        )
        assert mock_stub.call_count == 0, (
            f"force_on raw={raw!r}: stub unexpectedly called (count={mock_stub.call_count})"
        )


def test_use_llm_env_fallback_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #16 three-branch fallback contract within env-gate-accept arm.

    Distinct from fo68 Part B (two arms with symmetric observable shapes):
    fo69 Part B has three arms with **asymmetric** call-count signatures,
    pinning each fallback path independently.

    1. **No-model fallback**: ``_selected_model_for_run`` returns ``None``,
       the ``if model:`` check at line 684 skips the LLM body entirely ->
       stub is the only thing called.
    2. **LLM-raises fallback**: the LLM is called once and raises; the bare
       ``except Exception: pass`` arm at line 696 swallows it; stub then
       fires. A refactor that narrows or removes ``except`` would surface
       LLM exceptions to callers instead of degrading silently -- Part B
       catches it.
    3. **LLM-ok control**: the ``return`` at line 695 suppresses stub
       after a successful LLM call. A refactor that removes the ``return``
       would double-emit the plan stage (LLM + stub) -- Part B catches it.
    """
    orch, _store = make_dev_orchestrator()
    rid = orch.create_run("default")
    monkeypatch.setenv("HERMES_USE_LLM", "1")

    with _patched_execute(orch, model_id=None) as (mock_llm, mock_stub):
        orch.execute_plan_stage(rid)
    assert mock_llm.call_count == 0, (
        f"no_model: LLM unexpectedly called (count={mock_llm.call_count})"
    )
    assert mock_stub.call_count == 1, (
        f"no_model: stub not called once (count={mock_stub.call_count})"
    )

    with _patched_execute(orch, llm_raises=True) as (mock_llm, mock_stub):
        orch.execute_plan_stage(rid)
    assert mock_llm.call_count == 1, (
        f"llm_raises: LLM call count != 1 (count={mock_llm.call_count})"
    )
    assert mock_stub.call_count == 1, (
        f"llm_raises: stub not called once after LLM raised (count={mock_stub.call_count})"
    )

    with _patched_execute(orch, llm_raises=False) as (mock_llm, mock_stub):
        orch.execute_plan_stage(rid)
    assert mock_llm.call_count == 1, f"llm_ok: LLM call count != 1 (count={mock_llm.call_count})"
    assert mock_stub.call_count == 0, (
        f"llm_ok: stub unexpectedly called (count={mock_stub.call_count})"
    )


def test_use_llm_env_fail_closed_string_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #16 asymmetric fail-closed string-arm at the env gate.

    Loops 12 fail-closed variants spanning four sub-contracts (parallel
    to fo65 / 66 / 67 / 68 Part C). The double assertion (LLM not called
    AND stub called) is stronger than a single-sided check -- a refactor
    that calls *both* paths regardless of env fails the LLM-count check;
    a refactor that calls *neither* fails the stub-count check.

    With ``_patched_execute(model_id='dev:primary', llm_raises=False)``,
    if the env-gate had accepted the variant the LLM path would succeed
    and ``mock_llm.call_count`` would be 1; the assertion fails loudly
    in that case.

    1. **Env-absent** -- the production default skips the LLM branch
       entirely.
    2. **No ``.strip()``** -- whitespace-padded canonical fail-closed
       because ``.lower()`` alone does not trim whitespace. A future
       refactor adding ``.strip()`` silently flips ``" 1 "`` from
       "stub path" to "LLM path" -- this test fails loudly.
    3. **``"on"`` / ``"off"`` asymmetry** vs YAML coercer -- the env
       layer excludes ``"on"`` from the truthy tuple even though the
       workflow YAML coercer accepts it.
    4. **Single-tuple membership** -- case-folded falsy and unknown
       tokens both fail-closed via the same ``in`` predicate.
    """
    orch, _store = make_dev_orchestrator()
    rid = orch.create_run("default")
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
            monkeypatch.delenv("HERMES_USE_LLM", raising=False)
        else:
            monkeypatch.setenv("HERMES_USE_LLM", raw)
        with _patched_execute(orch) as (mock_llm, mock_stub):
            orch.execute_plan_stage(rid)
        assert mock_llm.call_count == 0, (
            f"fail_closed raw={raw!r}: LLM unexpectedly called (count={mock_llm.call_count})"
        )
        assert mock_stub.call_count == 1, (
            f"fail_closed raw={raw!r}: stub not called once (count={mock_stub.call_count})"
        )
