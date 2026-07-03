from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from orchestrator.launch.launch_test_llm import launch_test_llm_enabled
from orchestrator.launch.launch_test_stage import (
    MAX_LAUNCH_TEST_WRITE_ATTEMPTS,
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
    assert any(item.get("attempt") == 1 for item in write.findings if "attempt" in item)


def test_launch_test_write_replans_on_critique_fail(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text(
        "<html><body><button>Go</button></body></html>",
        encoding="utf-8",
    )
    calls = {"n": 0}

    def fake_critique(workspace, *, flow_id="launch_draft"):
        calls["n"] += 1
        if calls["n"] < 2:
            return type(
                "R",
                (),
                {
                    "passed": False,
                    "detail": "FAIL",
                    "critique_verdict": "FAIL",
                    "findings": [{"error": "positional_css_locator"}],
                },
            )()
        return run_launch_test_critique(workspace, flow_id=flow_id)

    with patch(
        "orchestrator.launch.launch_test_stage.run_launch_test_critique",
        side_effect=fake_critique,
    ):
        result = run_launch_test_write(tmp_path, flow_id="launch_draft")
    assert result.passed is True
    assert calls["n"] >= 2


def test_launch_test_write_exhausts_replan_attempts(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html><body></body></html>", encoding="utf-8")

    def always_fail(workspace, *, flow_id="launch_draft"):
        return type(
            "R",
            (),
            {
                "passed": False,
                "detail": "FAIL",
                "critique_verdict": "FAIL",
                "findings": [{"error": "missing id"}],
            },
        )()

    with patch(
        "orchestrator.launch.launch_test_stage.run_launch_test_critique",
        side_effect=always_fail,
    ):
        result = run_launch_test_write(tmp_path, flow_id="launch_draft")
    assert result.passed is False
    assert "replan_exhausted" in result.detail
    assert len([f for f in result.findings if f.get("attempt")]) == MAX_LAUNCH_TEST_WRITE_ATTEMPTS


def test_launch_test_llm_disabled_without_model(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_USE_LLM", raising=False)
    monkeypatch.delenv("NIMBUSWARE_LAUNCH_TEST_WRITER_MODEL", raising=False)
    assert launch_test_llm_enabled() is False
