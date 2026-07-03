from __future__ import annotations

from pathlib import Path
from typing import Any

from config.workflow_read import parse_agent_evaluator_workflow_block
from console.explainer_core.env_summaries import (
    env_disable_flag_summary,
    env_tri_state_summary,
)
from env.env_flags import nimbusware_use_llm_enabled
from orchestrator.workflow_agent_evaluator import agent_evaluator_stage_would_emit


def _nimbusware_agent_evaluator_env_summary() -> dict[str, Any]:
    return env_tri_state_summary("NIMBUSWARE_AGENT_EVALUATOR")


def _nimbusware_agent_evaluator_auto_promote_env_summary() -> dict[str, Any]:
    return env_disable_flag_summary(
        "NIMBUSWARE_AGENT_EVALUATOR_AUTO_PROMOTE",
        disable_key="disables_auto_promote",
    )


def _nimbusware_agent_evaluator_auto_create_env_summary() -> dict[str, Any]:
    return env_disable_flag_summary(
        "NIMBUSWARE_AGENT_EVALUATOR_AUTO_CREATE",
        disable_key="disables_auto_create",
    )


def _would_emit_agent_evaluator_stage(repo_root: Path, workflow_profile: str | None) -> bool:
    return agent_evaluator_stage_would_emit(repo_root, workflow_profile)


def _would_emit_llm_evaluation(repo_root: Path, workflow_profile: str | None) -> bool:
    if not _would_emit_agent_evaluator_stage(repo_root, workflow_profile):
        return False
    if not nimbusware_use_llm_enabled():
        return False
    block = parse_agent_evaluator_workflow_block(repo_root, workflow_profile)
    return block.llm_evaluation_enabled
