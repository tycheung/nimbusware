"""Stage graph foundation ."""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_orchestrator.merge import load_yaml
from hermes_orchestrator.stage_graph import (
    KNOWN_STAGE_GRAPH_STAGES,
    default_stage_graph,
    stage_graph_from_workflow_profile,
    stage_graph_metadata_snapshot,
    topological_order,
    validate_stage_graph,
)
from hermes_orchestrator.workflow_profiles import workflow_profile_dict
from nimbusware_config.keys import NS_WORKFLOWS
from nimbusware_config.materializer import ConfigMaterializer
from nimbusware_config.seed import seed_config_from_repo
from nimbusware_config.store import InMemoryConfigStore
from nimbusware_env import find_repo_root


def test_default_stage_graph_topological_order() -> None:
    graph = default_stage_graph()
    ordered = topological_order(graph)
    assert ordered[0] == "plan"
    assert "implementation" in ordered
    assert ordered.index("implementation.critique") > ordered.index("implementation")


def test_stage_graph_from_profile_when_key_absent() -> None:
    graph = stage_graph_from_workflow_profile({"version": 1})
    assert len(graph.nodes) == len(default_stage_graph().nodes)


def test_stage_graph_rejects_cycle() -> None:
    profile = {
        "stage_graph": [
            {"stage_name": "plan", "depends_on": ["implementation"]},
            {"stage_name": "implementation", "depends_on": ["plan"]},
        ],
    }
    graph = stage_graph_from_workflow_profile(profile)
    with pytest.raises(ValueError, match="cycle"):
        validate_stage_graph(graph, KNOWN_STAGE_GRAPH_STAGES)


def test_stage_graph_rejects_missing_dependency() -> None:
    profile = {
        "stage_graph": [
            {"stage_name": "plan", "depends_on": ["missing_parent"]},
        ],
    }
    graph = stage_graph_from_workflow_profile(profile)
    with pytest.raises(ValueError, match="not defined"):
        validate_stage_graph(graph, KNOWN_STAGE_GRAPH_STAGES)


def test_stage_graph_rejects_duplicate_stage_name() -> None:
    profile = {
        "stage_graph": [
            {"stage_name": "plan", "depends_on": []},
            {"stage_name": "plan", "depends_on": []},
        ],
    }
    graph = stage_graph_from_workflow_profile(profile)
    with pytest.raises(ValueError, match="duplicate"):
        validate_stage_graph(graph, KNOWN_STAGE_GRAPH_STAGES)


def test_stage_graph_metadata_snapshot_parallel_groups() -> None:
    graph = default_stage_graph()
    snap = stage_graph_metadata_snapshot(graph)
    assert snap["parallel_groups"]["writers"] == [
        "implementation",
        "test_writer",
        "frontend_writer",
    ]
    assert snap["ordered_stage_names"][0] == "plan"


def test_materializer_round_trip_default_workflow_stage_graph() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    store = InMemoryConfigStore()
    seed_config_from_repo(root, store)
    mat = ConfigMaterializer(root, store=store, use_db=True)
    disk = load_yaml(root / "configs" / "workflows" / "default.yaml")
    assert "stage_graph" in disk
    loaded = workflow_profile_dict(root, "default", materializer=mat)
    graph = stage_graph_from_workflow_profile(loaded)
    validate_stage_graph(graph, KNOWN_STAGE_GRAPH_STAGES)


def test_materializer_invalid_graph_profile(tmp_path: Path) -> None:
    bad = {
        "version": 1,
        "stage_graph": [
            {"stage_name": "plan", "depends_on": ["implementation"]},
            {"stage_name": "implementation", "depends_on": ["plan"]},
        ],
    }
    store = InMemoryConfigStore()
    store.upsert(NS_WORKFLOWS, "bad_graph", bad)
    mat = ConfigMaterializer(tmp_path, store=store, use_db=True)
    loaded = workflow_profile_dict(tmp_path, "bad_graph", materializer=mat)
    graph = stage_graph_from_workflow_profile(loaded)
    with pytest.raises(ValueError, match="cycle"):
        validate_stage_graph(graph, KNOWN_STAGE_GRAPH_STAGES)
