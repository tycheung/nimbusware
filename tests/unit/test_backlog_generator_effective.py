from __future__ import annotations

import pytest

from nimbusware_orchestrator.backlog_generator import effective_backlog_generator_mode


def test_effective_backlog_stays_stub_without_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_USE_LLM", raising=False)
    mode, reason = effective_backlog_generator_mode("stub")
    assert mode == "stub"
    assert reason


def test_effective_backlog_upgrades_stub_when_llm_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_BACKLOG_GENERATOR_MODEL", "llama3.2")
    mode, reason = effective_backlog_generator_mode("stub")
    assert mode == "llm"
    assert reason is None


def test_effective_backlog_llm_policy_falls_back_without_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    monkeypatch.delenv("NIMBUSWARE_BACKLOG_GENERATOR_MODEL", raising=False)
    mode, reason = effective_backlog_generator_mode("llm")
    assert mode == "stub"
    assert "BACKLOG_GENERATOR_MODEL" in (reason or "")
