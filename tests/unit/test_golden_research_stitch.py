"""Golden fixtures for research + stitch pipeline (no live network)."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from agent_core.models import EventType
from nimbusware_config.materializer import ConfigMaterializer
from nimbusware_config.seed import seed_config_from_repo
from nimbusware_config.store import InMemoryConfigStore
from nimbusware_env import find_repo_root
from nimbusware_orchestrator.pipeline import RunOrchestrator, default_paths
from nimbusware_store.memory import InMemoryEventStore

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_golden_golf_domain_research_brief(monkeypatch: pytest.MonkeyPatch) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    req = _load_json(_FIXTURES / "research" / "golf_domain" / "requirements.json")
    base, _ = default_paths(root)
    cfg_store = InMemoryConfigStore()
    seed_config_from_repo(root, cfg_store)
    mat = ConfigMaterializer(root, store=cfg_store, use_db=True)
    ev_store = InMemoryEventStore()
    orch = RunOrchestrator(
        ev_store,
        mat.get_role_registry(),
        repo_root=root,
        base_config_path=base,
        config_materializer=mat,
    )
    monkeypatch.setenv("NIMBUSWARE_RESEARCH", "1")
    run_id = orch.create_run(
        "default",
        requirements={"business_prompt": req["business_prompt"]},
    )
    orch.execute_plan_stage(run_id)
    briefs = [
        r
        for r in ev_store.list_run_events(str(run_id))
        if r.get("event_type") == EventType.RESEARCH_BRIEF_EMITTED.value
    ]
    domain = next(b for b in briefs if (b.get("payload") or {}).get("brief_kind") == "domain")
    assert "golf" in str((domain.get("payload") or {}).get("domain_tag", "")).lower()


def test_golden_auth_transplant_pipeline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    req = _load_json(_FIXTURES / "research" / "golf_domain" / "requirements.json")
    expected_path = _FIXTURES / "stitch" / "auth_transplant" / "expected_event_types.txt"
    expected_types = [
        line.strip()
        for line in expected_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    base, _ = default_paths(root)
    cfg_store = InMemoryConfigStore()
    seed_config_from_repo(root, cfg_store)
    mat = ConfigMaterializer(root, store=cfg_store, use_db=True)
    ev_store = InMemoryEventStore()
    ws = tmp_path / "auth_ws"
    ws.mkdir()
    orch = RunOrchestrator(
        ev_store,
        mat.get_role_registry(),
        repo_root=root,
        base_config_path=base,
        config_materializer=mat,
    )
    monkeypatch.setenv("NIMBUSWARE_RESEARCH", "1")
    monkeypatch.setenv("NIMBUSWARE_STITCH", "1")
    run_id = orch.create_run(
        "default",
        project_id=uuid4(),
        project_name="auth-transplant-golden",
        project_workspace_path=str(ws),
        requirements={"business_prompt": req["business_prompt"]},
    )
    orch.execute_plan_stage(run_id)
    types = [str(r.get("event_type") or "") for r in ev_store.list_run_events(str(run_id))]
    assert EventType.RUN_FAILED.value not in types
    for expected in expected_types:
        assert expected in types
    stages = [
        (r.get("payload") or {}).get("stage_name")
        for r in ev_store.list_run_events(str(run_id))
        if r.get("event_type") == EventType.STAGE_STARTED.value
    ]
    assert "refactor.post_stitch" in stages
