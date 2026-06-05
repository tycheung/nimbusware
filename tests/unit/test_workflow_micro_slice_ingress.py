"""micro_slice workflow validates against known stage graph."""

from __future__ import annotations

from pathlib import Path

from nimbusware_orchestrator.ingress import assert_known_workflow, assert_stage_graph_valid
from nimbusware_env import find_repo_root


def test_micro_slice_workflow_profile_validates() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    assert_known_workflow(root, "micro_slice")
    assert_stage_graph_valid(root, "micro_slice")
