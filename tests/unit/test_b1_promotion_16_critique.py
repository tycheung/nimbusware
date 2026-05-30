"""B1 promotion proof for §14 #16 — default-on universal critique on production profile."""

from __future__ import annotations
from nimbusware_env import find_repo_root

from pathlib import Path

import pytest

from hermes_orchestrator.pipeline import make_dev_orchestrator
from hermes_orchestrator.workflow_universal_critique import (
    effective_universal_critique,
    universal_critique_production_default_on,
)

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_production_default_on_without_env_kill() -> None:
    assert universal_critique_production_default_on(ROOT, "nimbusware_production") is True
    eff = effective_universal_critique(ROOT, "nimbusware_production")
    assert eff.impl_stub is True
    assert eff.tw_enabled is True


def test_create_run_freezes_production_critique_flags() -> None:
    orch, mem = make_dev_orchestrator(repo_root=ROOT)
    rid = orch.create_run("nimbusware_production")
    created = next(
        r for r in mem.list_run_events(str(rid))
        if r["event_type"] == "run.created"
    )
    uc = (created.get("metadata") or {}).get("universal_critique_effective") or {}
    assert uc.get("production_default_on") is True
    assert uc.get("impl_stub") is True


def test_kill_switch_disables_production_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HERMES_STUB_IMPLEMENTATION_CRITICS", "0")
    assert universal_critique_production_default_on(ROOT, "nimbusware_production") is False
