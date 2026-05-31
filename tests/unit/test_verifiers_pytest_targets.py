"""Scoped pytest helper for micro-slices."""

from __future__ import annotations

from pathlib import Path

from hermes_orchestrator.verifiers import run_pytest_targets
from nimbusware_env import find_repo_root


def test_run_pytest_targets_on_existing_test() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    code, out = run_pytest_targets(
        repo,
        ["tests/unit/test_micro_slice.py"],
        timeout_seconds=120.0,
    )
    assert code == 0
    assert "passed" in out.lower() or code == 0
