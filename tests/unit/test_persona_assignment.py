from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import app
from config.materializer import ConfigMaterializer
from config.seed import seed_config_from_repo
from config.store import InMemoryConfigStore
from env import find_repo_root
from orchestrator.ingress import assert_persona_assignment_valid
from orchestrator.pipeline import RunOrchestrator, default_paths
from store.memory import InMemoryEventStore


def test_create_run_freezes_persona_assignment_metadata() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    base, _ = default_paths(root)
    store = InMemoryConfigStore()
    seed_config_from_repo(root, store)
    mat = ConfigMaterializer(root, store=store, use_db=True)
    ev_store = InMemoryEventStore()
    orch = RunOrchestrator(
        ev_store,
        mat.get_role_registry(),
        repo_root=root,
        base_config_path=base,
        config_materializer=mat,
    )
    run_id = orch.create_run(
        "default",
        business_area_persona_id="commerce",
        development_role_persona_id="backend_engineer",
    )
    rows = ev_store.list_run_events(str(run_id))
    created = next(r for r in rows if r.get("event_type") == "run.created")
    pa = created["metadata"]["persona_assignment"]
    assert pa["business_area"] == "commerce"
    assert pa["development_role"] == "backend_engineer"


def test_unknown_business_area_persona_rejected() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    base, _ = default_paths(root)
    store = InMemoryConfigStore()
    seed_config_from_repo(root, store)
    mat = ConfigMaterializer(root, store=store, use_db=True)
    orch = RunOrchestrator(
        InMemoryEventStore(),
        mat.get_role_registry(),
        repo_root=root,
        base_config_path=base,
        config_materializer=mat,
    )
    with pytest.raises(ValueError, match="business_area_persona_id"):
        orch.create_run("default", business_area_persona_id="not-a-real-persona-xyz")


def test_assert_persona_assignment_wrong_shelf() -> None:
    from config.persist import load_persona_shelf

    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    shelf = load_persona_shelf(root)
    with pytest.raises(ValueError, match="development_role"):
        assert_persona_assignment_valid(
            shelf,
            development_role_persona_id="commerce",
        )


def test_api_create_run_with_persona_assignment() -> None:
    from api.deps import get_orchestrator

    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    base, _ = default_paths(root)
    store_cfg = InMemoryConfigStore()
    seed_config_from_repo(root, store_cfg)
    mat = ConfigMaterializer(root, store=store_cfg, use_db=True)
    ev_store = InMemoryEventStore()
    orch = RunOrchestrator(
        ev_store,
        mat.get_role_registry(),
        repo_root=root,
        base_config_path=base,
        config_materializer=mat,
    )

    app.dependency_overrides[get_orchestrator] = lambda: orch
    try:
        with TestClient(app) as c:
            r = c.post(
                "/v1/runs",
                json={
                    "workflow_profile": "default",
                    "business_area_persona_id": "commerce",
                    "development_role_persona_id": "backend_engineer",
                },
            )
            assert r.status_code == 200, r.text
            run_id = r.json()["run_id"]
            rows = ev_store.list_run_events(run_id)
            created = next(x for x in rows if x.get("event_type") == "run.created")
            assert created["metadata"]["persona_assignment"]["business_area"] == "commerce"
    finally:
        app.dependency_overrides.pop(get_orchestrator, None)
