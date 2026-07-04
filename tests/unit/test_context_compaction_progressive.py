from __future__ import annotations

from pathlib import Path

import pytest

from agent_core.agent_full_compact import (
    agent_compact_mode,
    maybe_full_compact_messages,
)
from agent_core.tool_output_offload import offload_path, prepare_tool_output_for_llm
from agent_tools.agent_loop import _append_tool_result, _LoopContext, _maybe_dedup_tool_messages


def test_tool_output_offload_writes_preview(tmp_path: Path) -> None:
    big = "x" * 8000
    llm, path = prepare_tool_output_for_llm(
        big,
        workspace=tmp_path,
        run_id="slice-1",
        step=3,
    )
    assert path is not None
    assert path.is_file()
    assert path.read_text(encoding="utf-8") == big
    assert "[offloaded" in llm
    assert len(llm) < len(big)


def test_tool_output_offload_skips_small_payload(tmp_path: Path) -> None:
    small = "hello"
    llm, path = prepare_tool_output_for_llm(
        small,
        workspace=tmp_path,
        run_id="slice-1",
        step=1,
    )
    assert path is None
    assert llm == small


def test_offload_path_is_under_cache(tmp_path: Path) -> None:
    p = offload_path(tmp_path, "run/a", 7)
    assert ".cache/nimbusware/tool-output" in p.as_posix()


def test_read_dedup_supersedes_prior_message() -> None:
    messages: list[dict[str, str]] = [{"role": "system", "content": "sys"}]
    ctx = _LoopContext()
    ctx.turn = 1
    _append_tool_result(
        messages,
        tool="read",
        output="first content",
        ok=True,
        ctx=ctx,
    )
    _maybe_dedup_tool_messages(
        messages,
        ctx=ctx,
        tool="read",
        arguments={"path": "packages/demo/app.py"},
    )
    ctx.turn = 2
    _append_tool_result(
        messages,
        tool="read",
        output="second content",
        ok=True,
        ctx=ctx,
    )
    _maybe_dedup_tool_messages(
        messages,
        ctx=ctx,
        tool="read",
        arguments={"path": "packages/demo/app.py"},
    )
    assert messages[1]["content"] == "[superseded by turn 2]"
    assert "second content" in messages[2]["content"]


def test_full_compact_reduces_message_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_AGENT_COMPACT", "full")
    monkeypatch.setenv("NIMBUSWARE_AGENT_CONTEXT_WINDOW", "8000")
    assert agent_compact_mode() == "full"
    messages = [
        {"role": "system", "content": "stable"},
        {"role": "user", "content": "slice plan"},
    ]
    for i in range(20):
        messages.append({"role": "assistant", "content": f"step {i} " + ("y" * 2000)})
        messages.append({"role": "user", "content": f"Tool read (ok):\n{'z' * 2000}"})
    compacted, saved = maybe_full_compact_messages(messages)
    assert len(compacted) < len(messages)
    assert saved > 0
    assert any("Compacted prior turns" in m.get("content", "") for m in compacted)
