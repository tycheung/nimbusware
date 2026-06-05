"""B2 promotion: YAML-first ungated self-refinement."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from nimbusware_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_orchestrator.workflow_self_refinement import (
    parse_self_refinement_workflow_block,
    self_refinement_production_ungated_effective,
    self_refinement_ungated_loop_effective,
)
from nimbusware_env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_production_ungated_effective_from_yaml() -> None:
    assert (
        self_refinement_production_ungated_effective(
            ROOT,
            "self_refinement_production_ungated",
        )
        is True
    )
    block = parse_self_refinement_workflow_block(
        ROOT,
        "self_refinement_production_ungated",
    )
    assert self_refinement_ungated_loop_effective(block) is True


def test_create_run_freezes_ungated_flags() -> None:
    orch, mem = make_dev_orchestrator(repo_root=ROOT)
    rid = orch.create_run("self_refinement_production_ungated")
    created = next(r for r in mem.list_run_events(str(rid)) if r["event_type"] == "run.created")
    sr = (created.get("metadata") or {}).get("self_refinement_effective") or {}
    assert sr.get("production_ungated") is True
    assert sr.get("ungated_loop") is True


@patch.dict(os.environ, {"NIMBUSWARE_SELF_REFINEMENT_STAGE_MARKER": "1"}, clear=False)
def test_production_ungated_auto_continues_without_env_override() -> None:
    os.environ.pop("NIMBUSWARE_SELF_REFINEMENT_UNGATED_LOOP", None)
    orch, mem = make_dev_orchestrator(repo_root=ROOT)
    rid = orch.create_run("self_refinement_production_ungated")
    orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001
    orch._maybe_continue_ungated_self_refinement_loop(rid)  # noqa: SLF001
    signals = [
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == "self_refinement.loop.signalled"
    ]
    assert len(signals) >= 2
    assert (signals[-1].get("payload") or {}).get("attempt") >= 2
