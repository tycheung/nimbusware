"""Runtime loaders use materialized T2 config."""

from __future__ import annotations

from pathlib import Path

from hermes_orchestrator.critique_routing import load_critique_router
from hermes_orchestrator.integrator_gate import load_integrator_gate_emit_enabled
from hermes_orchestrator.pipeline import RunOrchestrator, default_paths
from hermes_orchestrator.workflow_escalation import parse_escalation_workflow_block
from hermes_store.memory import InMemoryEventStore
from nimbusware_config.keys import (
    KEY_CRITIQUE_PAIRINGS,
    KEY_INTEGRATOR_THRESHOLDS,
    NS_PERSONAS,
    NS_POLICY,
)
from nimbusware_config.materializer import ConfigMaterializer
from nimbusware_config.seed import seed_config_from_repo
from nimbusware_config.store import InMemoryConfigStore
from nimbusware_env import find_repo_root


def _seed_minimal_run_store(root: Path, tmp_path: Path) -> ConfigMaterializer:
    store = InMemoryConfigStore()
    seed_config_from_repo(root, store)
    return ConfigMaterializer(tmp_path, store=store, use_db=True)


def test_parse_escalation_without_workflow_file_on_disk(tmp_path: Path) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    mat = _seed_minimal_run_store(root, tmp_path)
    block = parse_escalation_workflow_block(
        tmp_path,
        "escalation_suppress_on",
        config_materializer=mat,
    )
    assert isinstance(block.suppress_automatic_escalation, bool)


def test_load_critique_router_from_db_only(tmp_path: Path) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    store = InMemoryConfigStore()
    pairings = root / "configs" / "personas" / "critique_pairings.yaml"
    from hermes_orchestrator.merge import load_yaml

    store.upsert(NS_PERSONAS, KEY_CRITIQUE_PAIRINGS, load_yaml(pairings))
    mat = ConfigMaterializer(tmp_path, store=store, use_db=True)
    file_router = load_critique_router(root)
    db_router = load_critique_router(tmp_path, mat)
    assert file_router.known_producer_keys() == db_router.known_producer_keys()


def test_create_run_with_db_config_no_t2_files_on_disk(tmp_path: Path, monkeypatch) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    store = InMemoryConfigStore()

    seed_config_from_repo(root, store)
    mat = ConfigMaterializer(tmp_path, store=store, use_db=True)
    base, _ = default_paths(root)
    reg = mat.get_role_registry()
    orch = RunOrchestrator(
        InMemoryEventStore(),
        reg,
        repo_root=root,
        base_config_path=base,
        config_materializer=mat,
    )
    monkeypatch.setenv("HERMES_SKIP_PREFLIGHT", "1")
    run_id = orch.create_run("default")
    assert run_id is not None

    esc_path = tmp_path / "configs" / "escalation" / "policy.yaml"
    assert not esc_path.is_file()


def test_integrator_thresholds_from_materializer_only(tmp_path: Path) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    store = InMemoryConfigStore()
    from hermes_orchestrator.merge import load_yaml

    raw = load_yaml(root / "configs" / "integrator" / "thresholds.yaml")
    store.upsert(NS_POLICY, KEY_INTEGRATOR_THRESHOLDS, raw)
    mat = ConfigMaterializer(tmp_path, store=store, use_db=True)
    assert load_integrator_gate_emit_enabled(tmp_path, config_materializer=mat) == bool(
        raw.get("enabled", False),
    )
