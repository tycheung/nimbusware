"""RunOrchestrator.create_run`` cross-gate ordering meta-contract."""


from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import pytest

from hermes_orchestrator.pipeline import make_dev_orchestrator

_REPO_ROOT = Path(__file__).resolve().parents[1]

_GATE_NAMES: list[str] = [
    "assert_known_workflow",
    "assert_bundle_catalog_maps_resolve",
    "assert_persona_shelves_valid",
    "assert_agent_evaluator_persona_in_shelves",
    "assert_taxonomy_keys_resolve",
]

_GATE_MODULE = "hermes_orchestrator.pipeline"


# Sentinel exception classes/messages, one per gate, so each test
# can tell which gate fired without ambiguity. The class choices
# mirror the actual gate behaviour (FNF for the path/file gates,
# KeyError for the taxonomy lookup gate, ValueError otherwise).
_GATE_EXCEPTIONS: list[tuple[str, type[Exception], str]] = [
    ("assert_known_workflow", ValueError, "fo83-gate1-sentinel"),
    ("assert_bundle_catalog_maps_resolve", FileNotFoundError, "fo83-gate2-sentinel"),
    ("assert_persona_shelves_valid", ValueError, "fo83-gate3-sentinel"),
    ("assert_agent_evaluator_persona_in_shelves", ValueError, "fo83-gate4-sentinel"),
    ("assert_taxonomy_keys_resolve", KeyError, "fo83-gate5-sentinel"),
]


def _make_recorder(gate_name: str, calls: list[str]) -> Callable[..., None]:
    """Build a no-op recorder closure for ``gate_name`` (factory avoids late-binding)."""

    def _recorder(*_args: object, **_kwargs: object) -> None:
        calls.append(gate_name)

    return _recorder


def _make_raiser(exc_class: type[Exception], message: str) -> Callable[..., None]:
    """Build a closure that raises ``exc_class(message)`` (factory avoids late-binding)."""

    def _raiser(*_args: object, **_kwargs: object) -> None:
        raise exc_class(message)

    return _raiser


def _make_recorder_raiser(
    gate_name: str,
    message: str,
    calls: list[str],
) -> Callable[..., None]:
    """Build a closure that records its call AND raises (used in Part C for the N+1 gate)."""

    def _fn(*_args: object, **_kwargs: object) -> None:
        calls.append(gate_name)
        raise RuntimeError(message)

    return _fn


def _install_recorder_for_all_gates(
    monkeypatch: pytest.MonkeyPatch,
    calls: list[str],
) -> None:
    """Replace each of the 5 gates in the pipeline namespace with a recorder."""
    for name in _GATE_NAMES:
        monkeypatch.setattr(f"{_GATE_MODULE}.{name}", _make_recorder(name, calls))


def _install_raiser_for_gate(
    monkeypatch: pytest.MonkeyPatch,
    gate_name: str,
    exc_class: type[Exception],
    message: str,
) -> None:
    """Replace a single gate in the pipeline namespace with a raiser."""
    monkeypatch.setattr(f"{_GATE_MODULE}.{gate_name}", _make_raiser(exc_class, message))


def test_create_run_gate_chain_forward_call_order_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin the forward call sequence of the 5 pre-flight gates.

    All 5 gates are patched to recorders that append their name to a
    shared list; ``create_run("default")`` is then called against a
    real-repo orchestrator (which proceeds past the gates and emits
    a ``RUN_CREATED`` event -- irrelevant to this test). After the
    call, the recorder list MUST equal the canonical sequence at
    [pipeline.py:154-158](d:\\Hermes\\packages\\hermes_orchestrator\\pipeline.py)
    AND each gate MUST have fired exactly once (a future refactor
    that adds caching / retry around a gate without thinking about
    invariants would fail loudly here).
    """
    calls: list[str] = []
    _install_recorder_for_all_gates(monkeypatch, calls)
    orch, _mem = make_dev_orchestrator()
    orch.create_run("default")
    assert calls == _GATE_NAMES, (
        f"gate call order {calls} does not match expected {_GATE_NAMES}; "
        f"pipeline.py:154-158 ordering broken"
    )
    for name in _GATE_NAMES:
        count = calls.count(name)
        assert count == 1, (
            f"gate {name!r} called {count} times; expected exactly 1 "
            f"(double-invocation suggests a caching/retry refactor regression)"
        )


def test_create_run_per_gate_isolation_and_early_fail_order_matrix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin per-gate isolation + early-fail-order across all 5 gates.

    For each gate N, patch ONLY gate N to raise its sentinel
    exception; leave the others as real implementations. Call
    ``create_run("default")`` on a fresh ``make_dev_orchestrator()``
    and assert two properties:

    1. **Propagation**: the sentinel exception class and message
       bubble up unchanged -- no swallow, no transformation, no
       wrap. This pins ``create_run`` as a true raise-through frame
       for every gate.
    2. **Early-fail-order**: ``InMemoryEventStore._rows`` is empty
       after the failure -- no events were appended before the
       gate fired, so a failed ``create_run`` leaves zero partial
       state (extends fo80's gate-1 assertion to all 5 gates).

    This is the **architectural guarantee** that a future refactor
    moving any gate AFTER ``self._store.append`` at
    [pipeline.py:198](d:\\Hermes\\packages\\hermes_orchestrator\\pipeline.py)
    would break -- and this test catches it.
    """
    for gate_name, exc_class, message in _GATE_EXCEPTIONS:
        with monkeypatch.context() as m:
            _install_raiser_for_gate(m, gate_name, exc_class, message)
            orch, mem = make_dev_orchestrator()
            with pytest.raises(exc_class, match=re.escape(message)) as exc_info:
                orch.create_run("default")
            assert message in str(exc_info.value), (
                f"gate {gate_name!r} exception message {exc_info.value!r} "
                f"missing sentinel {message!r}; propagation broken"
            )
            assert mem._rows == [], (  # noqa: SLF001
                f"InMemoryEventStore has {len(mem._rows)} rows after gate "  # noqa: SLF001
                f"{gate_name!r} raised; expected 0 (early-fail-order broken "
                f"at pipeline.py:154-158 -- a gate moved after store.append?)"
            )


def test_create_run_gate_chain_pairwise_short_circuit_priority_matrix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin pairwise short-circuit priority across the 4 adjacent gate pairs.

    For each adjacent pair (N, N+1) in
    [(1,2), (2,3), (3,4), (4,5)]:

    1. Patch gate N to raise its sentinel (the "first to fail").
    2. Patch gate N+1 to **record-then-raise** a different sentinel
       (``RuntimeError("fo83-gateN+1-sentinel")``) -- this is the
       "should never fire" probe.
    3. Call ``create_run("default")``.
    4. Assert gate N's exception class and message are what
       surfaced (NOT the ``RuntimeError`` probe).
    5. Assert gate N+1's recorder list is empty -- gate N+1 was
       never reached, proving the chain short-circuited on gate N.

    This is the **strict** ordering proof: if ``create_run``
    mistakenly invoked gate N+1 before gate N (or in parallel /
    out-of-order), gate N+1's ``RuntimeError`` would surface OR its
    recorder would fire. Both branches are caught.
    """
    pairs = [
        (_GATE_EXCEPTIONS[i], _GATE_EXCEPTIONS[i + 1])
        for i in range(len(_GATE_EXCEPTIONS) - 1)
    ]
    for (n_name, n_class, n_msg), (np1_name, _np1_class, np1_msg) in pairs:
        np1_calls: list[str] = []
        with monkeypatch.context() as m:
            _install_raiser_for_gate(m, n_name, n_class, n_msg)
            m.setattr(
                f"{_GATE_MODULE}.{np1_name}",
                _make_recorder_raiser(np1_name, np1_msg, np1_calls),
            )
            orch, mem = make_dev_orchestrator()
            with pytest.raises(n_class, match=re.escape(n_msg)) as exc_info:
                orch.create_run("default")
            assert n_msg in str(exc_info.value), (
                f"pair ({n_name!r}, {np1_name!r}): expected gate {n_name!r} "
                f"sentinel {n_msg!r} in surfaced exception but got "
                f"{exc_info.value!r}; short-circuit ordering broken"
            )
            assert np1_calls == [], (
                f"pair ({n_name!r}, {np1_name!r}): gate {np1_name!r} fired "
                f"after gate {n_name!r} raised (np1_calls={np1_calls!r}); "
                f"short-circuit ordering broken at pipeline.py:154-158"
            )
            assert mem._rows == [], (  # noqa: SLF001
                f"pair ({n_name!r}, {np1_name!r}): InMemoryEventStore has "
                f"{len(mem._rows)} rows after pair failure; "  # noqa: SLF001
                f"expected 0 (early-fail-order broken)"
            )
