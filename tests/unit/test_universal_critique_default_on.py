"""Default-on universal critique workflow ."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_core.models import EventType
from nimbusware_orchestrator.workflow_universal_critique import (
    effective_universal_critique,
    parse_universal_critique_workflow_block,
    universal_critique_production_default_on,
)
from nimbusware_api.routes.runs import universal_critique_timeline_summary
from nimbusware_env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_default_on_yaml_enables_panels_without_explicit_enabled() -> None:
    block = parse_universal_critique_workflow_block(ROOT, "universal_critique_on")
    assert block.default_enabled is True
    assert block.impl_stub is True
    assert block.tw_enabled is True
    assert block.pll_enabled is True


def test_effective_universal_critique_default_on_flags() -> None:
    eff = effective_universal_critique(ROOT, "universal_critique_on")
    assert eff.default_enabled is True
    assert eff.impl_stub is True
    assert eff.tw_enabled is True
    assert eff.pll_enabled is True


@pytest.mark.parametrize(
    "env_key",
    [
        "NIMBUSWARE_ENABLE_TEST_WRITER_CRITIQUE",
        "NIMBUSWARE_ENABLE_PLANNER_CRITIQUE",
        "NIMBUSWARE_STUB_IMPLEMENTATION_CRITICS",
    ],
)
def test_env_kill_switch_overrides_default_on(
    env_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(env_key, "0")
    eff = effective_universal_critique(ROOT, "universal_critique_on")
    if env_key == "NIMBUSWARE_STUB_IMPLEMENTATION_CRITICS":
        assert eff.impl_stub is False
    elif env_key == "NIMBUSWARE_ENABLE_TEST_WRITER_CRITIQUE":
        assert eff.tw_enabled is False
    elif env_key == "NIMBUSWARE_ENABLE_PLANNER_CRITIQUE":
        assert eff.pll_enabled is False


def test_universal_critique_timeline_summary_default_enabled_effective() -> None:
    events = [
        {
            "event_type": EventType.RUN_CREATED.value,
            "metadata": {
                "universal_critique_effective": {
                    "default_enabled": True,
                    "production_default_on": True,
                    "unanimous_gate_enforce": True,
                },
            },
        },
        {
            "event_type": EventType.GATE_DECISION_EMITTED.value,
            "payload": {"stage_name": "planner.critique", "verdict": "PASS"},
        },
    ]
    uc = universal_critique_timeline_summary(events)
    assert uc is not None
    assert uc.get("default_enabled_effective") is True
    assert uc.get("unanimous_gate_effective") is True
    assert uc.get("production_default_on") is True


def test_universal_critique_production_default_on_without_env_kill() -> None:
    assert universal_critique_production_default_on(ROOT, "universal_critique_on") is True


def test_universal_critique_production_default_on_kill_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_ENABLE_TEST_WRITER_CRITIQUE", "0")
    assert universal_critique_production_default_on(ROOT, "universal_critique_on") is False


def test_default_profile_stays_off_without_default_enabled() -> None:
    block = parse_universal_critique_workflow_block(ROOT, "default")
    assert block.default_enabled is False
    assert block.tw_enabled is False
