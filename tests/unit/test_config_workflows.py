"""Workflow profile materialization."""

from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_config.keys import NS_WORKFLOWS
from nimbusware_config.materializer import ConfigMaterializer
from nimbusware_config.seed import seed_config_from_repo
from nimbusware_config.store import InMemoryConfigStore
from nimbusware_env import find_repo_root
from nimbusware_orchestrator.ingress import assert_known_workflow
from nimbusware_orchestrator.merge import load_yaml
from nimbusware_orchestrator.pipeline import RunOrchestrator, default_paths
from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict
from nimbusware_store.memory import InMemoryEventStore


def test_default_profile_from_materializer_matches_file() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    store = InMemoryConfigStore()
    seed_config_from_repo(root, store)
    mat = ConfigMaterializer(root, store=store, use_db=True)
    disk = load_yaml(root / "configs" / "workflows" / "default.yaml")
    assert mat.get_workflow_profile_dict("default") == disk
    assert workflow_profile_dict(root, "default", materializer=mat) == disk


def test_assert_known_workflow_db_only_without_file(tmp_path: Path) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    wf = load_yaml(root / "configs" / "workflows" / "default.yaml")
    store = InMemoryConfigStore()
    store.upsert(NS_WORKFLOWS, "default", wf)
    mat = ConfigMaterializer(tmp_path, store=store, use_db=True)
    assert_known_workflow(tmp_path, "default", config_materializer=mat)
    wf_path = tmp_path / "configs" / "workflows" / "default.yaml"
    assert not wf_path.is_file()


def test_create_run_with_materialized_config(monkeypatch: pytest.MonkeyPatch) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    base, _ = default_paths(root)
    store = InMemoryConfigStore()
    seed_config_from_repo(root, store)
    mat = ConfigMaterializer(root, store=store, use_db=True)
    reg = mat.get_role_registry()
    orch = RunOrchestrator(
        InMemoryEventStore(),
        reg,
        repo_root=root,
        base_config_path=base,
        config_materializer=mat,
    )
    monkeypatch.setenv("NIMBUSWARE_SKIP_PREFLIGHT", "1")
    run_id = orch.create_run("default")
    assert run_id is not None


def test_materializer_stage_graph_profile_round_trip() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    store = InMemoryConfigStore()
    seed_config_from_repo(root, store)
    mat = ConfigMaterializer(root, store=store, use_db=True)
    loaded = mat.get_workflow_profile_dict("default")
    assert isinstance(loaded.get("stage_graph"), list)
    from nimbusware_orchestrator.stage_graph import (
        KNOWN_STAGE_GRAPH_STAGES,
        stage_graph_from_workflow_profile,
        validate_stage_graph,
    )

    graph = stage_graph_from_workflow_profile(loaded)
    validate_stage_graph(graph, KNOWN_STAGE_GRAPH_STAGES)
