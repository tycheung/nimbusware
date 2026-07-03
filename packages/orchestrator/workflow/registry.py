"""Central registry for workflow module loaders and re-exports.

Maps each ``workflow_*.py`` module stem to its primary loader callable so call
sites can import from here instead of individual workflow modules.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from orchestrator.workflow.agent_evaluator import (
    AgentEvaluatorAutoCreatePersonaBlock,
    AgentEvaluatorWorkflowBlock,
    PersonaCoverageCritiqueBlock,
    agent_evaluator_llm_branch_effective,
    agent_evaluator_llm_stub_env_enabled,
    agent_evaluator_production_default_on,
    agent_evaluator_production_llm_fallback_enabled,
    agent_evaluator_rules_derived_llm_evaluation,
    agent_evaluator_stage_would_emit,
    parse_agent_evaluator_workflow_block,
    persona_coverage_critique_effective,
    persona_coverage_critique_llm_branch_effective,
)
from orchestrator.workflow.blocks_simple import (
    DevEnvWorkflowBlock,
    EscalationWorkflowBlock,
    FastSliceWorkflowBlock,
    IntegrationAdapterWriterWorkflowBlock,
    MicroSliceWorkflowBlock,
    TheaterWorkflowBlock,
    dev_env_effective_metadata,
    fast_slice_effective_metadata,
    parse_dev_env_workflow_block,
    parse_escalation_workflow_block,
    parse_fast_slice_workflow_block,
    parse_integration_adapter_writer_workflow_block,
    parse_micro_slice_workflow_block,
    parse_theater_workflow_block,
    theater_effective_metadata,
)
from orchestrator.workflow.campaign import (
    BacklogWorkflowBlock,
    CampaignWorkflowBlock,
    CompletionWorkflowBlock,
    MaintenanceWorkflowBlock,
    campaign_effective_metadata,
    campaign_policy_from_blocks,
    parse_backlog_workflow_block,
    parse_campaign_workflow_block,
    parse_completion_workflow_block,
    parse_maintenance_workflow_block,
)
from orchestrator.workflow.memory import (
    MemoryWorkflowBlock,
    memory_effective_metadata,
    parse_memory_workflow_block,
    run_memory_retrieval_enabled,
)
from orchestrator.workflow.parallel_critics import (
    ParallelCriticsWorkflowBlock,
    parallel_critics_enabled,
    parse_parallel_critics_workflow_block,
)
from orchestrator.workflow.parallel_writers import (
    ParallelWritersWorkflowBlock,
    parallel_writers_enabled,
    parse_parallel_writers_workflow_block,
    test_writer_llm_body_enabled,
    test_writer_llm_stub_fallback,
    test_writer_stage_enabled,
)
from orchestrator.workflow.patch import (
    PatchAutoApplyPolicy,
    PatchWorkflowBlock,
    parse_patch_workflow_block,
    patch_effective_metadata,
)
from orchestrator.workflow.probation_automation import (
    ProbationAutomationWorkflowBlock,
    parse_probation_automation_workflow_block,
    probation_automation_effective_metadata,
)
from orchestrator.workflow.refactor import (
    RefactorWorkflowBlock,
    parse_refactor_workflow_block,
    refactor_stage_effective,
)
from orchestrator.workflow.research import (
    ResearchWorkflowBlock,
    StitchWorkflowBlock,
    parse_research_workflow_block,
    parse_stitch_workflow_block,
    research_effective_metadata,
    stitch_effective_metadata,
)
from orchestrator.workflow.scan_critique import (
    ScanCritiqueBlock,
    network_resilience_critique_effective,
    network_resilience_critique_llm_branch_effective,
    parse_network_resilience_critique_workflow_block,
    parse_performance_critique_workflow_block,
    parse_scan_critique_workflow_block,
    parse_security_critique_workflow_block,
    performance_critique_effective,
    performance_critique_llm_branch_effective,
    scan_critique_gate_timeline_summary,
    security_critique_effective,
    security_critique_llm_branch_effective,
    severity_for_critique_floor,
)
from orchestrator.workflow.security import security_scan_metadata_on_verify_enabled
from orchestrator.workflow.security_metadata import (
    parse_security_scan_metadata_on_verify_workflow,
)
from orchestrator.workflow.self_refinement import (
    SelfRefinementWorkflowBlock,
    parse_self_refinement_workflow_block,
    self_refinement_llm_critique_branch_effective,
    self_refinement_llm_critique_effective_for_run,
    self_refinement_production_ungated_effective,
    self_refinement_ungated_loop_effective,
)
from orchestrator.workflow.universal_critique import (
    EffectiveUniversalCritique,
    UniversalCritiqueWorkflowBlock,
    effective_universal_critique,
    parse_universal_critique_workflow_block,
    universal_critique_production_default_on,
)

WorkflowBlockLoader = Callable[..., Any]

WORKFLOW_MODULE_KEYS: frozenset[str] = frozenset(
    {
        "agent_evaluator",
        "campaign",
        "dev_env",
        "escalation",
        "fast_slice",
        "integration_adapter_writer",
        "memory",
        "micro_slice",
        "parallel_critics",
        "parallel_writers",
        "patch",
        "probation_automation",
        "refactor",
        "research",
        "scan_critique",
        "security",
        "security_metadata",
        "self_refinement",
        "theater",
        "universal_critique",
    }
)

WORKFLOW_MODULE_LOADERS: dict[str, WorkflowBlockLoader] = {
    "agent_evaluator": parse_agent_evaluator_workflow_block,
    "campaign": parse_campaign_workflow_block,
    "dev_env": parse_dev_env_workflow_block,
    "escalation": parse_escalation_workflow_block,
    "fast_slice": parse_fast_slice_workflow_block,
    "integration_adapter_writer": parse_integration_adapter_writer_workflow_block,
    "memory": parse_memory_workflow_block,
    "micro_slice": parse_micro_slice_workflow_block,
    "parallel_critics": parse_parallel_critics_workflow_block,
    "parallel_writers": parse_parallel_writers_workflow_block,
    "patch": parse_patch_workflow_block,
    "probation_automation": parse_probation_automation_workflow_block,
    "refactor": parse_refactor_workflow_block,
    "research": parse_research_workflow_block,
    "scan_critique": parse_security_critique_workflow_block,
    "security": security_scan_metadata_on_verify_enabled,
    "security_metadata": parse_security_scan_metadata_on_verify_workflow,
    "self_refinement": parse_self_refinement_workflow_block,
    "theater": parse_theater_workflow_block,
    "universal_critique": parse_universal_critique_workflow_block,
}

WORKFLOW_BLOCK_LOADERS: dict[str, WorkflowBlockLoader] = {
    **WORKFLOW_MODULE_LOADERS,
    "backlog": parse_backlog_workflow_block,
    "completion": parse_completion_workflow_block,
    "maintenance": parse_maintenance_workflow_block,
    "network_resilience_critique": parse_network_resilience_critique_workflow_block,
    "performance_critique": parse_performance_critique_workflow_block,
    "stitch": parse_stitch_workflow_block,
}


def get_workflow_block_loader(key: str) -> WorkflowBlockLoader:
    """Return the raw loader callable for ``key``.

    Prefer :func:`parse_workflow_block` at call sites — it invokes the loader
    with ``repo_root``, ``workflow_profile``, and optional ``config_materializer``.
    """
    try:
        return WORKFLOW_BLOCK_LOADERS[key]
    except KeyError:
        msg = f"unknown workflow block key: {key!r}"
        raise KeyError(msg) from None


def parse_workflow_block(
    key: str,
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> Any:
    return get_workflow_block_loader(key)(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )


__all__ = (
    "AgentEvaluatorAutoCreatePersonaBlock",
    "AgentEvaluatorWorkflowBlock",
    "BacklogWorkflowBlock",
    "CampaignWorkflowBlock",
    "CompletionWorkflowBlock",
    "DevEnvWorkflowBlock",
    "EffectiveUniversalCritique",
    "EscalationWorkflowBlock",
    "FastSliceWorkflowBlock",
    "IntegrationAdapterWriterWorkflowBlock",
    "MaintenanceWorkflowBlock",
    "MemoryWorkflowBlock",
    "MicroSliceWorkflowBlock",
    "ParallelCriticsWorkflowBlock",
    "ParallelWritersWorkflowBlock",
    "PatchAutoApplyPolicy",
    "PatchWorkflowBlock",
    "PersonaCoverageCritiqueBlock",
    "ProbationAutomationWorkflowBlock",
    "RefactorWorkflowBlock",
    "ResearchWorkflowBlock",
    "ScanCritiqueBlock",
    "SelfRefinementWorkflowBlock",
    "StitchWorkflowBlock",
    "TheaterWorkflowBlock",
    "UniversalCritiqueWorkflowBlock",
    "WORKFLOW_BLOCK_LOADERS",
    "WORKFLOW_MODULE_KEYS",
    "WORKFLOW_MODULE_LOADERS",
    "WorkflowBlockLoader",
    "agent_evaluator_llm_branch_effective",
    "agent_evaluator_llm_stub_env_enabled",
    "agent_evaluator_production_default_on",
    "agent_evaluator_production_llm_fallback_enabled",
    "agent_evaluator_rules_derived_llm_evaluation",
    "agent_evaluator_stage_would_emit",
    "campaign_effective_metadata",
    "campaign_policy_from_blocks",
    "dev_env_effective_metadata",
    "effective_universal_critique",
    "fast_slice_effective_metadata",
    "get_workflow_block_loader",
    "memory_effective_metadata",
    "network_resilience_critique_effective",
    "network_resilience_critique_llm_branch_effective",
    "parallel_critics_enabled",
    "parallel_writers_enabled",
    "parse_agent_evaluator_workflow_block",
    "parse_backlog_workflow_block",
    "parse_campaign_workflow_block",
    "parse_completion_workflow_block",
    "parse_dev_env_workflow_block",
    "parse_escalation_workflow_block",
    "parse_fast_slice_workflow_block",
    "parse_integration_adapter_writer_workflow_block",
    "parse_maintenance_workflow_block",
    "parse_memory_workflow_block",
    "parse_micro_slice_workflow_block",
    "parse_network_resilience_critique_workflow_block",
    "parse_parallel_critics_workflow_block",
    "parse_parallel_writers_workflow_block",
    "parse_patch_workflow_block",
    "parse_performance_critique_workflow_block",
    "parse_probation_automation_workflow_block",
    "parse_refactor_workflow_block",
    "parse_research_workflow_block",
    "parse_scan_critique_workflow_block",
    "parse_security_critique_workflow_block",
    "parse_security_scan_metadata_on_verify_workflow",
    "parse_self_refinement_workflow_block",
    "parse_stitch_workflow_block",
    "parse_theater_workflow_block",
    "parse_universal_critique_workflow_block",
    "parse_workflow_block",
    "patch_effective_metadata",
    "performance_critique_effective",
    "performance_critique_llm_branch_effective",
    "persona_coverage_critique_effective",
    "persona_coverage_critique_llm_branch_effective",
    "probation_automation_effective_metadata",
    "refactor_stage_effective",
    "research_effective_metadata",
    "run_memory_retrieval_enabled",
    "scan_critique_gate_timeline_summary",
    "security_critique_effective",
    "security_critique_llm_branch_effective",
    "security_scan_metadata_on_verify_enabled",
    "self_refinement_llm_critique_branch_effective",
    "self_refinement_llm_critique_effective_for_run",
    "self_refinement_production_ungated_effective",
    "self_refinement_ungated_loop_effective",
    "severity_for_critique_floor",
    "stitch_effective_metadata",
    "test_writer_llm_body_enabled",
    "test_writer_llm_stub_fallback",
    "test_writer_stage_enabled",
    "theater_effective_metadata",
    "universal_critique_production_default_on",
)
