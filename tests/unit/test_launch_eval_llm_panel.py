from __future__ import annotations

import pytest

from nimbusware_orchestrator.launch_evaluator import evaluate_workspace_rubric, llm_panel_enabled


def test_launch_eval_llm_panel_off_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_LAUNCH_EVAL_LLM", raising=False)
    (tmp_path / "README.md").write_text("# x\n", encoding="utf-8")
    scorecard = evaluate_workspace_rubric(tmp_path, min_aggregate=0.0)
    assert scorecard.llm_findings == ()


def test_launch_eval_llm_panel_opt_in(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("NIMBUSWARE_LAUNCH_EVAL_LLM", "1")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    assert llm_panel_enabled()
    scorecard = evaluate_workspace_rubric(tmp_path, min_aggregate=0.0)
    assert scorecard.llm_findings
    assert "advisory" in scorecard.llm_findings[0]


def test_launch_eval_llm_panel_uses_ollama_when_available(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_LAUNCH_EVAL_LLM", "1")

    def _fake_fetch(_workspace) -> tuple[str, ...]:
        return ("llm: strong test layout",)

    monkeypatch.setattr(
        "nimbusware_orchestrator.launch_evaluator.fetch_llm_rubric_findings",
        _fake_fetch,
    )
    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")
    scorecard = evaluate_workspace_rubric(tmp_path, min_aggregate=0.0)
    assert scorecard.llm_findings == ("llm: strong test layout",)
