"""create_run custom_agent_id metadata."""

from __future__ import annotations
from nimbusware_env import find_repo_root

from pathlib import Path
from uuid import uuid4

import pytest

from hermes_orchestrator.pipeline import make_dev_orchestrator


def test_create_run_unknown_custom_agent_raises() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, _mem = make_dev_orchestrator(repo)
    with pytest.raises(ValueError, match="custom_agent_id"):
        orch.create_run("default", custom_agent_id="does-not-exist")


def test_create_run_with_custom_agent() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("default", custom_agent_id="default_planner")
    rows = store.list_run_events(str(run_id))
    created = rows[0]
    meta = created.get("metadata") or {}
    assert meta.get("custom_agent", {}).get("id") == "default_planner"
