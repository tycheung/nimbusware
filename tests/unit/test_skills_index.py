from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_config.skills_index import (
    list_skill_briefs,
    load_skill,
    resolve_stage_skill,
    skill_briefs_prompt_block,
)
from nimbusware_env import find_repo_root


def test_list_skill_briefs_has_entries() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    briefs = list_skill_briefs(repo_root=root)
    assert len(briefs) >= 5
    assert all(len(b.description) <= 200 for b in briefs)


def test_load_skill_by_id() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    body = load_skill("refactor-rubric", repo_root=root)
    assert "Refactor rubric" in body


def test_load_skill_missing_raises() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    with pytest.raises(FileNotFoundError, match="unknown skill_id"):
        load_skill("does-not-exist", repo_root=root)


def test_skill_briefs_prompt_block_shorter_than_full_load() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    block = skill_briefs_prompt_block(repo_root=root)
    full = "\n".join(load_skill(b.id, repo_root=root) for b in list_skill_briefs(repo_root=root))
    assert len(block) < len(full)


def test_resolve_stage_skill() -> None:
    assert resolve_stage_skill({"skill": "skill:refactor-rubric"}) == "refactor-rubric"
    assert resolve_stage_skill({"skill": "plan-quality"}) == "plan-quality"
    assert resolve_stage_skill(None) is None
