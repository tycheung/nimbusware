from __future__ import annotations

import re

from agent_core.prompt_tiers import assemble_prompt, stable_slice_agent_block


def test_stable_prefix_identical_across_slices() -> None:
    stable = stable_slice_agent_block(tool_rules="Use edit for small changes.")
    a = assemble_prompt(stable=stable, volatile="Slice: slice-1")
    b = assemble_prompt(stable=stable, volatile="Slice: slice-2")
    assert a[0]["content"] == b[0]["content"]
    assert a[1]["content"] != b[1]["content"]


def test_no_timestamps_in_stable_block() -> None:
    stable = stable_slice_agent_block(tool_rules="Rules here.")
    messages = assemble_prompt(stable=stable, volatile="work")
    content = messages[0]["content"]
    assert not re.search(r"\d{4}-\d{2}-\d{2}", content)


def test_context_tier_appended_to_system() -> None:
    messages = assemble_prompt(
        stable="STABLE",
        context="CONTEXT",
        volatile="VOLATILE",
    )
    assert "STABLE" in messages[0]["content"]
    assert "CONTEXT" in messages[0]["content"]
    assert messages[1]["content"] == "VOLATILE"
