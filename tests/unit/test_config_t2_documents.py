"""T2 policy document materialization."""

from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_config.materializer import ConfigMaterializer
from nimbusware_config.seed import seed_config_from_repo
from nimbusware_config.store import InMemoryConfigStore
from nimbusware_env import find_repo_root
from nimbusware_orchestrator.merge import load_yaml


def test_t2_getters_match_on_disk_after_seed() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    store = InMemoryConfigStore()
    seed_config_from_repo(root, store)
    mat = ConfigMaterializer(root, store=store, use_db=True)

    assert mat.get_escalation_policy() == load_yaml(root / "configs" / "escalation" / "policy.yaml")
    assert mat.get_integrator_thresholds() == load_yaml(
        root / "configs" / "integrator" / "thresholds.yaml",
    )
    assert mat.get_self_refinement_policy() == load_yaml(
        root / "configs" / "self_refinement" / "policy.yaml",
    )
    assert mat.get_critique_pairings() == load_yaml(
        root / "configs" / "personas" / "critique_pairings.yaml",
    )
    assert mat.get_bundle_catalog() == load_yaml(root / "configs" / "bundles" / "catalog.yaml")


def test_missing_t2_row_raises_key_error(tmp_path: Path) -> None:
    store = InMemoryConfigStore()
    mat = ConfigMaterializer(tmp_path, store=store, use_db=True)
    with pytest.raises(KeyError, match="escalation"):
        mat.get_escalation_policy()
