"""P1 Research+Stitch core (fo510–fo515) — roles, events, stages, planner merge."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_core.models import EventType
from hermes_orchestrator.pipeline import RunOrchestrator, default_paths
from hermes_orchestrator.workflow_research import (
    parse_research_workflow_block,
    research_effective_metadata,
)
from hermes_research.artifacts import persist_research_brief, read_research_brief
from hermes_research.models import ResearchBrief, ResearchBriefSource
from hermes_research.planner_context import planner_research_context_from_events
from hermes_store.allowed_types import allowed_event_type_values
from hermes_store.memory import InMemoryEventStore
from nimbusware_config.materializer import ConfigMaterializer
from nimbusware_config.seed import seed_config_from_repo
from nimbusware_config.store import InMemoryConfigStore
from nimbusware_env import find_repo_root


def test_research_event_types_in_db_allowlist() -> None:
    allowed = allowed_event_type_values()
    for et in (
        EventType.RESEARCH_BRIEF_EMITTED,
        EventType.RESEARCH_PATTERN_INDEXED,
        EventType.DOMAIN_CRITIC_PROPOSED,
    ):
        assert et.value in allowed


def test_research_roles_resolve() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    store = InMemoryConfigStore()
    seed_config_from_repo(root, store)
    mat = ConfigMaterializer(root, store=store, use_db=True)
    reg = mat.get_role_registry()
    for key in ("domain_researcher", "code_researcher", "stitcher"):
        assert reg.resolve(key) is not None


def test_create_run_freezes_research_and_stitch_metadata() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
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
    run_id = orch.create_run("default")
    created = next(
        r for r in ev_store.list_run_events(str(run_id)) if r.get("event_type") == "run.created"
    )
    research = created["metadata"]["research"]
    stitch = created["metadata"]["stitch"]
    assert research["enabled"] is False
    assert research["domain_enabled"] is True
    assert stitch["enabled"] is False
    assert stitch["max_files"] == 40


def test_research_brief_round_trip(tmp_path: Path) -> None:
    brief = ResearchBrief(
        brief_kind="domain",
        domain_tag="golf",
        summary="Stub domain summary for tests.",
        artifact_id="test-brief-1",
        sources=(
            ResearchBriefSource(
                url="stub://domain/golf",
                license="MIT",
                trust_tier="high",
            ),
        ),
    )
    persist_research_brief(tmp_path, brief)
    loaded = read_research_brief(tmp_path, "test-brief-1")
    assert loaded is not None
    assert loaded.summary == brief.summary
    assert loaded.sources[0].license == "MIT"


def test_planner_context_from_research_events() -> None:
    rows = [
        {
            "event_type": EventType.RESEARCH_BRIEF_EMITTED.value,
            "payload": {
                "brief_kind": "domain",
                "domain_tag": "inventory",
                "summary": "Inventory domain constraints.",
                "artifact_id": "a1",
                "sources": [],
            },
        },
        {
            "event_type": EventType.RESEARCH_PATTERN_INDEXED.value,
            "payload": {
                "pattern_id": "p1",
                "repo_url": "stub://oss/example",
                "paths": ["lib/auth"],
                "license": "MIT",
                "embedding_ref": "det:p1",
            },
        },
    ]
    ctx = planner_research_context_from_events(rows)
    assert "Inventory domain" in ctx
    assert "Indexed pattern" in ctx


def test_execute_plan_stage_emits_research_with_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
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
    monkeypatch.setenv("HERMES_RESEARCH", "1")
    run_id = orch.create_run(
        "default",
        requirements={"business_prompt": "Build golf tee time scheduling."},
    )
    orch.execute_plan_stage(run_id)
    types = [r.get("event_type") for r in ev_store.list_run_events(str(run_id))]
    assert EventType.RESEARCH_BRIEF_EMITTED.value in types
    assert EventType.RESEARCH_PATTERN_INDEXED.value in types
    assert EventType.DOMAIN_CRITIC_PROPOSED.value in types
    ctx = planner_research_context_from_events(ev_store.list_run_events(str(run_id)))
    assert "golf" in ctx.lower() or "Domain research" in ctx


def test_parse_research_workflow_block_from_default() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    block = parse_research_workflow_block(root, "default")
    meta = research_effective_metadata(block)
    assert meta["max_brief_sources"] == 20
    assert meta["pattern_index_contribution"] is True
