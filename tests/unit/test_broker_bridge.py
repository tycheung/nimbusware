from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from broker_client import broker_llm_enabled, select_llm_backend
from orchestrator.llm.broker_bridge import try_broker_chat_json
from orchestrator.llm.chat_facade import ollama_chat_json_via_plan_patch


def test_try_broker_chat_json_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    assert try_broker_chat_json([{"role": "user", "content": "hi"}]) is None


def test_sak403_e_flag_and_bridge_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dual-run LLM flag gates broker_bridge routing (sak403-e epic closure)."""
    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    assert broker_llm_enabled() is False
    assert select_llm_backend() == "python"
    assert try_broker_chat_json([{"role": "user", "content": "hi"}]) is None

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    assert broker_llm_enabled() is True
    assert select_llm_backend() == "broker"


def test_try_broker_chat_json_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    with patch("orchestrator.llm.broker_bridge.llm_chat_via_broker") as mock_chat:
        mock_chat.return_value = {"answer": "42"}
        out = try_broker_chat_json([{"role": "user", "content": "hi"}], model="m1")
    mock_chat.assert_called_once_with([{"role": "user", "content": "hi"}], model="m1")
    assert out == {"answer": "42"}


def test_try_broker_chat_json_failure_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    with patch("orchestrator.llm.broker_bridge.llm_chat_via_broker") as mock_chat:
        mock_chat.side_effect = RuntimeError("broker down")
        assert try_broker_chat_json([{"role": "user", "content": "hi"}]) is None


def test_try_broker_chat_json_broker_only_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "2")
    with patch("orchestrator.llm.broker_bridge.llm_chat_via_broker") as mock_chat:
        mock_chat.side_effect = RuntimeError("broker down")
        with pytest.raises(RuntimeError, match="broker down"):
            try_broker_chat_json([{"role": "user", "content": "hi"}])


def test_ollama_chat_json_via_plan_patch_uses_broker_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    with patch("orchestrator.llm.chat_facade.try_broker_chat_json") as mock_bridge:
        mock_bridge.return_value = {"via": "broker"}
        out = ollama_chat_json_via_plan_patch(
            base_url="http://ollama",
            model="m",
            messages=[{"role": "user", "content": "x"}],
        )
    mock_bridge.assert_called_once()
    assert out == {"via": "broker"}


def test_ollama_chat_json_via_plan_patch_falls_back_when_bridge_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    resolver = MagicMock()
    resolver.chat_json.return_value = {"via": "resolver"}
    with (
        patch("orchestrator.llm.chat_facade.try_broker_chat_json", return_value=None),
        patch("orchestrator.model_routing.preflight.agent_role_for_stage", return_value="planner"),
        patch("orchestrator.collab.mesh_hydrate.ensure_mesh_binding_for_llm"),
        patch("env.find_repo_root", return_value="/repo"),
        patch("orchestrator.model_routing.resolver.ModelBindingResolver", return_value=resolver),
        patch("orchestrator.collab.mesh_context.mesh_participant_overrides", return_value={}),
        patch("orchestrator.collab.mesh_context.mesh_actor_user_id", return_value="u1"),
    ):
        out = ollama_chat_json_via_plan_patch(
            base_url="http://ollama",
            model="m",
            messages=[{"role": "user", "content": "x"}],
            stage_name="plan",
            agent_role="planner",
        )
    assert out == {"via": "resolver"}
    resolver.chat_json.assert_called_once()
