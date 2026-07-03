from __future__ import annotations

from pathlib import Path

from agent_core.prompt_tiers import assemble_prompt
from agent_tools.prompts import (
    build_agent_stable_prompt,
    load_agent_implement_stable_prompt,
)


def test_load_agent_implement_stable_from_config() -> None:
    root = Path(__file__).resolve().parents[2]
    text = load_agent_implement_stable_prompt(repo_root=root)
    assert "prefer edit over write" in text
    assert "Reply with JSON" in text


def test_stable_prefix_identical_across_slices() -> None:
    stable = build_agent_stable_prompt()
    a = assemble_prompt(stable=stable, volatile="Slice: slice-1")
    b = assemble_prompt(stable=stable, volatile="Slice: slice-2")
    assert a[0]["content"] == b[0]["content"]
