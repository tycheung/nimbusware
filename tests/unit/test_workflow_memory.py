from __future__ import annotations

from pathlib import Path

from nimbusware_orchestrator.micro_slice import parse_slice_plan
from nimbusware_orchestrator.workflow_memory import (
    memory_effective_metadata,
    memory_query_from_slice_plan,
    memory_settings_from_run_metadata,
    parse_memory_workflow_block,
    run_memory_retrieval_enabled,
)
from nimbusware_env import find_repo_root


def test_parse_memory_workflow_block_defaults() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    block = parse_memory_workflow_block(repo, "default")
    assert block.retrieval_enabled is True
    assert block.index_contribution is True


def test_parse_memory_workflow_block_production() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    block = parse_memory_workflow_block(repo, "nimbusware_production")
    assert block.retrieval_enabled is True
    assert block.retrieval_k == 5


def test_memory_effective_metadata_overrides() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    block = parse_memory_workflow_block(repo, "nimbusware_production")
    meta = memory_effective_metadata(
        block,
        run_policy_overrides={"memory": {"retrieval_enabled": False}},
    )
    assert meta["retrieval_enabled"] is False
    assert meta["index_contribution"] is True


def test_run_memory_retrieval_enabled_defaults() -> None:
    assert run_memory_retrieval_enabled({}) is True
    assert run_memory_retrieval_enabled({"memory": {"retrieval_enabled": False}}) is False


def test_memory_query_from_slice_plan() -> None:
    plan = parse_slice_plan({"slice_id": "s1", "target_paths": ["a.py"], "rationale": "fix sql"})
    q = memory_query_from_slice_plan(plan)
    assert "fix sql" in q
    assert "a.py" in q


def test_memory_settings_from_run_metadata() -> None:
    settings = memory_settings_from_run_metadata(
        {"memory": {"retrieval_k": 3, "excerpt_max_chars": 500}},
    )
    assert settings.retrieval_k == 3
    assert settings.excerpt_max_chars == 500
