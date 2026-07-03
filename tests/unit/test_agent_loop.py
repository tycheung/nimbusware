from __future__ import annotations

from pathlib import Path

import pytest

from agent_tools.agent_loop import run
from orchestrator.slice.micro_slice import parse_slice_plan


def test_agent_loop_reads_and_edits_via_tools(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    ws.mkdir()
    target = ws / "packages" / "demo" / "app.py"
    target.parent.mkdir(parents=True)
    target.write_text("def foo():\n    return 1\n", encoding="utf-8")
    plan = parse_slice_plan(
        {
            "slice_id": "slice-1",
            "target_paths": ["packages/demo/app.py"],
            "rationale": "fix foo",
        },
    )

    calls = {"n": 0}

    def fake_chat(**_kwargs: object) -> dict[str, object]:
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "done": False,
                "tool_calls": [{"tool": "read", "path": "packages/demo/app.py"}],
            }
        if calls["n"] == 2:
            return {
                "done": False,
                "tool_calls": [
                    {
                        "tool": "edit",
                        "path": "packages/demo/app.py",
                        "old_text": "return 1",
                        "new_text": "return 2",
                    },
                ],
            }
        return {"done": True, "summary": "updated foo"}

    result = run(
        ws,
        plan,
        base_url="http://127.0.0.1:11434",
        model_id="test",
        chat_fn=fake_chat,
    )
    assert result.exit_code == 0
    assert "packages/demo/app.py" in result.paths_touched
    assert "return 2" in target.read_text(encoding="utf-8")
    assert calls["n"] >= 2


def test_agent_loop_respects_tool_step_cap(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "a.py").write_text("x\n", encoding="utf-8")
    plan = parse_slice_plan(
        {"slice_id": "s1", "target_paths": ["a.py"], "rationale": "x"},
    )

    def endless_read(**_kwargs: object) -> dict[str, object]:
        return {"done": False, "tool_calls": [{"tool": "read", "path": "a.py"}]}

    from agent_tools.risk_caps import AgentRiskCaps

    result = run(
        ws,
        plan,
        base_url="http://127.0.0.1:11434",
        model_id="test",
        chat_fn=endless_read,
        risk_caps=AgentRiskCaps(max_tool_steps=1),
    )
    assert result.exit_code == 1
    assert result.tool_steps == 2
    assert any("max_tool_steps" in line for line in result.logs)


def test_jit_loop_skips_gather_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_SLICE_IMPLEMENT", "agent")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_AGENT_JIT_LOOP", "1")

    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "packages/demo").mkdir(parents=True)
    (ws / "packages/demo/app.py").write_text("x\n", encoding="utf-8")
    plan = parse_slice_plan(
        {"slice_id": "s1", "target_paths": ["packages/demo/app.py"]},
    )

    gather_called = {"v": False}

    def spy_gather(*_a: object, **_k: object) -> str:
        gather_called["v"] = True
        return ""

    monkeypatch.setattr(
        "agent_tools.runtime._gather_context",
        spy_gather,
    )

    from agent_tools.agent_loop import AgentLoopResult

    def fake_run(*_a: object, **_k: object) -> AgentLoopResult:
        return AgentLoopResult()

    monkeypatch.setattr(
        "agent_tools.agent_loop.run",
        fake_run,
    )

    from agent_tools.runtime import execute_slice_implement_agent

    execute_slice_implement_agent(
        ws,
        plan,
        llm_base_url="http://127.0.0.1:11434",
        llm_model_id="test",
    )
    assert gather_called["v"] is False
