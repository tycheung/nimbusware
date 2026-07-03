from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.workflow.parallel_critics import parallel_critics_enabled

_REPO = Path(__file__).resolve().parents[2]


def test_parallel_critics_disabled_on_medium_tier() -> None:
    assert not parallel_critics_enabled(
        _REPO,
        "default",
        resource_governor={"hardware_tier": "medium", "allow_parallel_critics": True},
    )


def test_parallel_critics_enabled_on_strong_tier_with_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_ALLOW_PARALLEL_CRITICS", "1")
    assert parallel_critics_enabled(
        _REPO,
        "default",
        resource_governor={"hardware_tier": "strong", "allow_parallel_critics": False},
    )


def test_parallel_critics_respects_force_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_ALLOW_PARALLEL_CRITICS", "0")
    assert not parallel_critics_enabled(
        _REPO,
        "default",
        resource_governor={"hardware_tier": "strong", "allow_parallel_critics": True},
    )
