from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import pytest

from env import find_repo_root
from orchestrator.pipeline import make_dev_orchestrator

_REPO_ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])

_GATE_NAMES: list[str] = [
    "assert_known_workflow",
    "assert_stage_graph_valid",
    "assert_bundle_catalog_maps_resolve",
    "assert_persona_shelves_valid",
    "assert_agent_evaluator_persona_in_shelves",
    "assert_taxonomy_keys_resolve",
    "assert_critique_coverage_complete",
]

_GATE_MODULE = "orchestrator._pipeline.create_run_preflight"


# Sentinel exception classes/messages, one per gate, so each test
# can tell which gate fired without ambiguity. The class choices
# mirror the actual gate behaviour (FNF for the path/file gates,
# KeyError for the taxonomy lookup gate, ValueError otherwise).
_GATE_EXCEPTIONS: list[tuple[str, type[Exception], str]] = [
    ("assert_known_workflow", ValueError, "fo83-gate1-sentinel"),
    ("assert_stage_graph_valid", ValueError, "fo83-gate2-sentinel"),
    ("assert_bundle_catalog_maps_resolve", FileNotFoundError, "fo83-gate3-sentinel"),
    ("assert_persona_shelves_valid", ValueError, "fo83-gate4-sentinel"),
    ("assert_agent_evaluator_persona_in_shelves", ValueError, "fo83-gate5-sentinel"),
    ("assert_taxonomy_keys_resolve", KeyError, "fo83-gate6-sentinel"),
    ("assert_critique_coverage_complete", ValueError, "fo83-gate7-sentinel"),
]


def _make_recorder(gate_name: str, calls: list[str]) -> Callable[..., None]:

    def _recorder(*_args: object, **_kwargs: object) -> None:
        calls.append(gate_name)

    return _recorder


def _make_raiser(exc_class: type[Exception], message: str) -> Callable[..., None]:

    def _raiser(*_args: object, **_kwargs: object) -> None:
        raise exc_class(message)

    return _raiser


def _make_recorder_raiser(
    gate_name: str,
    message: str,
    calls: list[str],
) -> Callable[..., None]:

    def _fn(*_args: object, **_kwargs: object) -> None:
        calls.append(gate_name)
        raise RuntimeError(message)

    return _fn


def _install_recorder_for_all_gates(
    monkeypatch: pytest.MonkeyPatch,
    calls: list[str],
) -> None:
    for name in _GATE_NAMES:
        monkeypatch.setattr(f"{_GATE_MODULE}.{name}", _make_recorder(name, calls))


def _install_raiser_for_gate(
    monkeypatch: pytest.MonkeyPatch,
    gate_name: str,
    exc_class: type[Exception],
    message: str,
) -> None:
    monkeypatch.setattr(f"{_GATE_MODULE}.{gate_name}", _make_raiser(exc_class, message))


def test_create_run_gate_chain_forward_call_order_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    pairs = [
        (_GATE_EXCEPTIONS[i], _GATE_EXCEPTIONS[i + 1]) for i in range(len(_GATE_EXCEPTIONS) - 1)
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
