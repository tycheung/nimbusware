"""Roles registry materialization parity."""

from __future__ import annotations

from pathlib import Path

from nimbusware_config.materializer import ConfigMaterializer
from nimbusware_config.seed import seed_config_from_repo
from nimbusware_config.store import InMemoryConfigStore
from nimbusware_env import find_repo_root
from nimbusware_orchestrator.registry import RoleRegistry


def test_db_registry_matches_yaml_seed() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    yaml_reg = RoleRegistry.from_yaml(root / "configs" / "roles.yaml")
    store = InMemoryConfigStore()
    seed_config_from_repo(root, store)
    mat = ConfigMaterializer(root, store=store, use_db=True)
    db_reg = mat.get_role_registry()
    for key in ("planner", "backend_writer", "test_writer"):
        assert yaml_reg.resolve(key) == db_reg.resolve(key)
    assert yaml_reg.yaml_version == db_reg.yaml_version


def test_unknown_taxonomy_fails_create_run_ingress() -> None:
    from nimbusware_orchestrator.ingress import assert_taxonomy_keys_resolve

    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    store = InMemoryConfigStore()
    seed_config_from_repo(root, store)
    mat = ConfigMaterializer(root, store=store, use_db=True)
    reg = mat.get_role_registry()
    import pytest

    with pytest.raises(KeyError):
        assert_taxonomy_keys_resolve(reg, ["not_a_real_taxonomy_key_xyz"])
