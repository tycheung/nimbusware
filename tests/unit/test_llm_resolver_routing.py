from __future__ import annotations

from unittest.mock import MagicMock, patch

from orchestrator.llm.common import ollama_chat_json_via_plan_patch
from orchestrator.routing.preflight import agent_role_for_stage


def test_agent_role_for_stage_maps_slice_and_critique() -> None:
    assert agent_role_for_stage("slice.plan") == "planner"
    assert agent_role_for_stage("implementation.critique") == "security_critic"
    assert agent_role_for_stage("frontend_writer.critique") == "frontend_writer"
    assert agent_role_for_stage("unknown.stage") is None


def test_via_plan_patch_uses_resolver_for_mapped_stage() -> None:
    fake = {"verdict": "PASS"}
    resolver = MagicMock()
    resolver.chat_json.return_value = fake
    with patch(
        "orchestrator.routing.resolver.ModelBindingResolver",
        return_value=resolver,
    ):
        out = ollama_chat_json_via_plan_patch(
            base_url="http://localhost:11434",
            model="m",
            messages=[{"role": "user", "content": "hi"}],
            stage_name="slice.plan",
        )
    assert out == fake
    resolver.chat_json.assert_called_once_with(
        "planner",
        messages=[{"role": "user", "content": "hi"}],
        timeout_seconds=120.0,
        participant_overrides=None,
        actor_user_id="",
        cache_blocks=None,
        stage_name="slice.plan",
    )
