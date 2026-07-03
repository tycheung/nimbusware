from __future__ import annotations

from pathlib import Path

from agent_core.models import EventType
from env import find_repo_root
from orchestrator.backlog_generator import (
    emit_backlog_generated,
    generate_heuristic_backlog,
)
from orchestrator.maintenance_architecture import run_maintenance_architecture
from orchestrator.pipeline import make_dev_orchestrator


def test_architecture_pass_revises_backlog() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("campaign_micro_slice")
    backlog = generate_heuristic_backlog(str(run_id), max_slices=2)
    emit_backlog_generated(store, run_id, backlog)
    run_maintenance_architecture(orch, run_id, slices_completed=2)
    types = [r.get("event_type") for r in store.list_run_events(str(run_id))]
    assert EventType.DELIVERY_BACKLOG_REVISED.value in types
