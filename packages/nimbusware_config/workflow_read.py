from __future__ import annotations

from nimbusware_orchestrator.merge import load_yaml
from nimbusware_orchestrator.workflow_agent_evaluator import parse_agent_evaluator_workflow_block
from nimbusware_orchestrator.workflow_escalation import parse_escalation_workflow_block
from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict, workflow_profile_path
from nimbusware_orchestrator.workflow_security import security_scan_metadata_on_verify_enabled
from nimbusware_orchestrator.workflow_security_metadata import (
    parse_security_scan_metadata_on_verify_workflow,
)
from nimbusware_orchestrator.workflow_self_refinement import (
    SelfRefinementWorkflowBlock,
    parse_self_refinement_workflow_block,
)
from nimbusware_orchestrator.workflow_universal_critique import (
    effective_universal_critique,
    parse_universal_critique_workflow_block,
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
]


def escalation_policy_breadth(repo_root):  # type: ignore[no-untyped-def]
    """Lazy import — optional policy breadth helper for escalation explainers."""
    from nimbusware_orchestrator.escalation_policy_breadth import escalation_policy_breadth as _fn

    return _fn(repo_root)
