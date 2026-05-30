"""create_run requirements metadata."""

from __future__ import annotations

from pathlib import Path

from hermes_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_env import find_repo_root
from nimbusware_maker.intent import build_requirements_artifact


def test_create_run_with_requirements_metadata() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    requirements = build_requirements_artifact(
        business_prompt="Inventory tracker",
        clarifications=[{"question_id": "audience", "question": "Who?", "answer": "Staff"}],
    )
    run_id = orch.create_run("default", requirements=requirements)
    rows = store.list_run_events(str(run_id))
    meta = rows[0].get("metadata") or {}
    assert meta.get("requirements", {}).get("business_prompt") == "Inventory tracker"
