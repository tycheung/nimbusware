from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.merge import load_yaml
from orchestrator.workflow.profiles import workflow_profile_dict, workflow_profile_path
from orchestrator.workflow.registry import (
    SelfRefinementWorkflowBlock,
    effective_universal_critique,
    parse_agent_evaluator_workflow_block,
    parse_escalation_workflow_block,
    parse_security_scan_metadata_on_verify_workflow,
    parse_self_refinement_workflow_block,
    parse_universal_critique_workflow_block,
    security_scan_metadata_on_verify_enabled,
)

__all__ = [
    "SelfRefinementWorkflowBlock",
    "effective_universal_critique",
    "load_yaml",
    "parse_agent_evaluator_workflow_block",
    "parse_escalation_workflow_block",
    "parse_security_scan_metadata_on_verify_workflow",
    "parse_self_refinement_workflow_block",
    "parse_universal_critique_workflow_block",
    "security_scan_metadata_on_verify_enabled",
    "workflow_profile_dict",
    "workflow_profile_path",
    "escalation_policy_breadth",
]


def escalation_policy_breadth(repo_root: Path) -> dict[str, Any]:
    """Lazy import — optional policy breadth helper for escalation explainers."""
    from orchestrator.escalation_policy_breadth import escalation_policy_breadth as _fn

    return _fn(repo_root)
