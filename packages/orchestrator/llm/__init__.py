"""orchestrator.llm after sak411 — broker_bridge + facades (`sak431` / `sak497-j`).

Plan + agent_evaluator policy LLM folded into gate_helpers (`sak522-a/b` / `sak498-d`).
"""

from __future__ import annotations

from typing import Any

from agent_core.critique_stages import (
    FRONTEND_WRITER_CRITIQUE_STAGE,
    IMPLEMENTATION_CRITIQUE_STAGE,
    MODULE_INTEGRATOR_CRITIQUE_STAGE,
    PLANNER_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
)
from orchestrator.llm.broker_bridge import try_broker_chat_json
from orchestrator.llm.chat_facade import ollama_chat_json_via_plan_patch
from orchestrator.llm.gate_helpers import (  # sak522-a/b / sak498-d
    emit_stub_plan_stage,
    execute_agent_evaluator_policy_llm,
    execute_plan_stage_llm,
)
from orchestrator.llm.post_verify_role_bindings import (  # sak497-j / sak498-c
    emit_stub_frontend_writer_critique_panel,
    emit_stub_implementation_critique_panel,
    emit_stub_module_integrator_critique_panel,
    emit_stub_planner_critique_panel,
    emit_stub_self_refinement_critique_panel,
    emit_stub_test_writer_critique_panel,
    execute_frontend_writer_critique_llm,
    execute_implementation_critique_llm,
    execute_module_integrator_critique_llm,
    execute_planner_critique_llm,
    execute_self_refinement_critique_llm,
    execute_test_writer_critique_llm,
)

_MSG = "local LLM path removed (sak411); use broker llm bind / SwissArmyNoife"


def _removed(*_args: Any, **_kwargs: Any) -> Any:
    raise RuntimeError(_MSG)


# sak497-j: local modules deleted under peel — call sites refuse under LLM=1|2 (sak496-b).

__all__ = [
    "FRONTEND_WRITER_CRITIQUE_STAGE",
    "IMPLEMENTATION_CRITIQUE_STAGE",
    "MODULE_INTEGRATOR_CRITIQUE_STAGE",
    "PLANNER_CRITIQUE_STAGE",
    "TEST_WRITER_CRITIQUE_STAGE",
    "emit_stub_frontend_writer_critique_panel",
    "emit_stub_implementation_critique_panel",
    "emit_stub_module_integrator_critique_panel",
    "emit_stub_plan_stage",
    "emit_stub_planner_critique_panel",
    "emit_stub_self_refinement_critique_panel",
    "emit_stub_test_writer_critique_panel",
    "execute_agent_evaluator_policy_llm",
    "execute_frontend_writer_critique_llm",
    "execute_implementation_critique_llm",
    "execute_module_integrator_critique_llm",
    "execute_plan_stage_llm",
    "execute_planner_critique_llm",
    "execute_self_refinement_critique_llm",
    "execute_test_writer_critique_llm",
    "ollama_chat_json_via_plan_patch",
    "try_broker_chat_json",
]
