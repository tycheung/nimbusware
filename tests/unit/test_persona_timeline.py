from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from agent_core.timeline_metadata import persona_assignment_from_run_created_metadata
from api.app import app
from api.deps import get_orchestrator, get_store
from config.materializer import ConfigMaterializer
from config.seed import seed_config_from_repo
from config.store import InMemoryConfigStore
from console.persona_assignment_display import (
    persona_assignment_caption,
    persona_assignment_from_timeline,
    persona_assignment_summary_rows,
)
from env import find_repo_root
from orchestrator.pipeline import RunOrchestrator, default_paths
from store.memory import InMemoryEventStore


def test_persona_assignment_from_run_created_metadata_normalizes_ids() -> None:
    pa = persona_assignment_from_run_created_metadata(
        {
            "persona_assignment": {
                "business_area": "commerce",
                "development_role": "backend_engineer",
            },
        },
    )
    assert pa == {
        "business_area": {"id": "commerce"},
        "development_role": {"id": "backend_engineer"},
    }


def test_persona_assignment_from_run_created_metadata_empty_when_missing() -> None:
    assert persona_assignment_from_run_created_metadata({}) is None
    assert persona_assignment_from_run_created_metadata({"persona_assignment": {}}) is None


def test_timeline_persona_assignment_from_api() -> None:
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
    app.dependency_overrides[get_store] = lambda: ev_store
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
            tl = c.get(f"/v1/runs/{run_id}/timeline")
            assert tl.status_code == 200, tl.text
            body = tl.json()
            assert body["persona_assignment"] == {
                "business_area": {"id": "commerce"},
                "development_role": {"id": "backend_engineer"},
            }
            detail = c.get(f"/v1/runs/{run_id}")
            assert detail.status_code == 200
            assert detail.json()["persona_assignment"] == body["persona_assignment"]
    finally:
        app.dependency_overrides.pop(get_orchestrator, None)
        app.dependency_overrides.pop(get_store, None)


def test_timeline_persona_assignment_absent_without_create_ids() -> None:
    with TestClient(app) as c:
        r = c.post("/v1/runs", json={"workflow_profile": "default"})
        assert r.status_code == 200
        run_id = r.json()["run_id"]
        tl = c.get(f"/v1/runs/{run_id}/timeline").json()
        assert tl.get("persona_assignment") is None


def test_console_persona_assignment_display_parsers() -> None:
    timeline = {
        "persona_assignment": {
            "business_area": {"id": "commerce"},
            "development_role": {"id": "backend_engineer"},
        },
    }
    pa = persona_assignment_from_timeline(timeline)
    assert pa is not None
    rows = persona_assignment_summary_rows(pa)
    assert any(r["field"] == "Business area id" and r["value"] == "commerce" for r in rows)
    cap = persona_assignment_caption(pa)
    assert cap is not None
    assert "commerce" in cap
    assert persona_assignment_from_timeline(None) is None
    assert persona_assignment_summary_rows(None) == []
