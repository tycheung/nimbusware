from __future__ import annotations

from pathlib import Path

from nimbusware_orchestrator.launch_test_stage import (
    build_launch_test_writer_prompt,
    run_launch_test_critique,
    run_launch_test_plan,
    run_launch_test_write,
)


def test_build_launch_test_writer_prompt_injects_pack(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"dependencies":{"react":"18"},"devDependencies":{"vite":"5"}}',
        encoding="utf-8",
    )
    prompt = build_launch_test_writer_prompt(tmp_path)
    assert "Launch Test Writer" in prompt
    assert "react_vite" in prompt


def test_launch_test_plan_and_write(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text(
        '<html><body><button>Go</button><input data-testid="x" /></body></html>',
        encoding="utf-8",
    )
    plan = run_launch_test_plan(tmp_path)
    assert plan.passed is True
    write = run_launch_test_write(tmp_path, flow_id="launch_draft")
    assert write.passed is True
    critique = run_launch_test_critique(tmp_path, flow_id="launch_draft")
    assert critique.passed is True
