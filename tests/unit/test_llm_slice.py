"""LLM slice planning helpers."""

from __future__ import annotations

from unittest.mock import patch

from nimbusware_orchestrator.llm_slice import execute_slice_plan_llm
from nimbusware_orchestrator.micro_slice import parse_slice_plan


def test_execute_slice_plan_llm_parses_response() -> None:
    rows = [
        {
            "event_type": "run.created",
            "metadata": {
                "custom_agent": {
                    "system_prompt_preview": "You are a test planner.",
                },
            },
        },
    ]
    fake = {
        "slice_id": "slice-llm-1",
        "rationale": "touch api",
        "target_paths": ["packages/nimbusware_api/app.py"],
        "acceptance_criteria": "tests pass",
    }
    with patch(
        "nimbusware_orchestrator.llm_slice.ollama_chat_json",
        return_value=fake,
    ):
        plan = execute_slice_plan_llm(
            rows=rows,
            base_url="http://localhost:11434",
            model_id="test-model",
            slice_index=1,
        )
    assert plan is not None
    assert plan.slice_id == "slice-llm-1"
    assert plan.target_paths[0].endswith("app.py")


def test_execute_slice_plan_llm_returns_none_on_failure() -> None:
    with patch(
        "nimbusware_orchestrator.llm_slice.ollama_chat_json",
        side_effect=RuntimeError("down"),
    ):
        plan = execute_slice_plan_llm(
            rows=[],
            base_url="http://localhost:11434",
            model_id="test-model",
        )
    assert plan is None


def test_stub_plan_still_valid() -> None:
    plan = parse_slice_plan({"slice_id": "s1", "target_paths": ["a.py"]})
    assert plan.slice_id == "s1"
