"""Policy snapshot from materialized config (P0-e)."""

from __future__ import annotations

from pathlib import Path

from nimbusware_config.materializer import ConfigMaterializer
from nimbusware_config.seed import seed_config_from_repo
from nimbusware_config.store import InMemoryConfigStore
from nimbusware_env import find_repo_root
from nimbusware_orchestrator.merge import (
    policy_snapshot_from_files,
    policy_snapshot_from_materializer,
)
from nimbusware_orchestrator.pipeline import RunOrchestrator, default_paths
from nimbusware_orchestrator.workflow_profiles import workflow_profile_path
from nimbusware_store.memory import InMemoryEventStore


def test_materialized_snapshot_matches_files_default_workflow() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    base, _ = default_paths(root)
    wf_path = workflow_profile_path(root, "default")
    from_files = policy_snapshot_from_files(base, wf_path, None)

    store = InMemoryConfigStore()
    seed_config_from_repo(root, store)
    mat = ConfigMaterializer(root, store=store, use_db=True)
    from_mat = policy_snapshot_from_materializer(mat, "default", None)
    assert from_mat.model_dump(mode="json") == from_files.model_dump(mode="json")


def test_create_run_snapshot_immutable_after_workflow_mutation() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    base, _ = default_paths(root)
    store_cfg = InMemoryConfigStore()
    seed_config_from_repo(root, store_cfg)
    mat = ConfigMaterializer(root, store=store_cfg, use_db=True)
    reg = mat.get_role_registry()
    ev_store = InMemoryEventStore()
    orch = RunOrchestrator(
        ev_store,
        reg,
        repo_root=root,
        base_config_path=base,
        config_materializer=mat,
    )
    run_id = orch.create_run(
        "default",
        run_policy_overrides={"network_egress": {"budget_bytes_per_run": 999}},
    )
    snap_before = orch.policy_snapshot_for_run(run_id)

    wf = dict(mat.get_workflow_profile_dict("default"))
    wf.setdefault("network_egress", {})["budget_bytes_per_run"] = 1
    mat.upsert_content("workflows", "default", wf)

    snap_after = orch.policy_snapshot_for_run(run_id)
    assert snap_before == snap_after
    assert snap_after.get("network_egress", {}).get("budget_bytes_per_run") == 999
