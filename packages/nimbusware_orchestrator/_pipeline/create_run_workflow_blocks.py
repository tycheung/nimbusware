from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator._pipeline._helpers import (
    effective_universal_critique,
    parse_agent_evaluator_workflow_block,
    parse_self_refinement_workflow_block,
    parse_universal_critique_workflow_block,
)
from nimbusware_orchestrator.workflow_campaign import (
    parse_backlog_workflow_block,
    parse_campaign_workflow_block,
    parse_completion_workflow_block,
    parse_maintenance_workflow_block,
)
from nimbusware_orchestrator.workflow_dev_env import parse_dev_env_workflow_block
from nimbusware_orchestrator.workflow_fast_slice import parse_fast_slice_workflow_block
from nimbusware_orchestrator.workflow_memory import (
    memory_effective_metadata,
    parse_memory_workflow_block,
    resolve_memory_index_version,
)
from nimbusware_orchestrator.workflow_micro_slice import parse_micro_slice_workflow_block
from nimbusware_orchestrator.workflow_patch import parse_patch_workflow_block
from nimbusware_orchestrator.workflow_probation_automation import (
    parse_probation_automation_workflow_block,
)
from nimbusware_orchestrator.workflow_research import (
    parse_research_workflow_block,
    parse_stitch_workflow_block,
)
from nimbusware_orchestrator.workflow_theater import parse_theater_workflow_block


@dataclass(frozen=True)
class CreateRunWorkflowBlocks:
    uc_block: Any
    uc_eff: Any
    ae_block: Any
    sr_block: Any
    prob_block: Any
    fs_block: Any
    patch_block: Any
    campaign_block: Any
    backlog_block: Any
    maintenance_block: Any
    completion_block: Any
    ms_block: Any
    mem_block: Any
    research_block: Any
    stitch_block: Any
    theater_block: Any
    dev_env_block: Any
    memory_meta: dict[str, Any]


def load_create_run_workflow_blocks(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None,
    memory_chunk_store: Any | None,
    run_policy_overrides: dict[str, Any] | None,
) -> CreateRunWorkflowBlocks:
    mat = config_materializer
    uc_block = parse_universal_critique_workflow_block(
        repo_root, workflow_profile, config_materializer=mat
    )
    uc_eff = effective_universal_critique(repo_root, workflow_profile, config_materializer=mat)
    ae_block = parse_agent_evaluator_workflow_block(
        repo_root, workflow_profile, config_materializer=mat
    )
    sr_block = parse_self_refinement_workflow_block(
        repo_root, workflow_profile, config_materializer=mat
    )
    prob_block = parse_probation_automation_workflow_block(
        repo_root, workflow_profile, config_materializer=mat
    )
    fs_block = parse_fast_slice_workflow_block(repo_root, workflow_profile, config_materializer=mat)
    patch_block = parse_patch_workflow_block(repo_root, workflow_profile, config_materializer=mat)
    campaign_block = parse_campaign_workflow_block(
        repo_root, workflow_profile, config_materializer=mat
    )
    backlog_block = parse_backlog_workflow_block(
        repo_root, workflow_profile, config_materializer=mat
    )
    maintenance_block = parse_maintenance_workflow_block(
        repo_root, workflow_profile, config_materializer=mat
    )
    completion_block = parse_completion_workflow_block(
        repo_root, workflow_profile, config_materializer=mat
    )
    ms_block = parse_micro_slice_workflow_block(
        repo_root, workflow_profile, config_materializer=mat
    )
    mem_block = parse_memory_workflow_block(repo_root, workflow_profile, config_materializer=mat)
    research_block = parse_research_workflow_block(
        repo_root, workflow_profile, config_materializer=mat
    )
    stitch_block = parse_stitch_workflow_block(repo_root, workflow_profile, config_materializer=mat)
    theater_block = parse_theater_workflow_block(
        repo_root, workflow_profile, config_materializer=mat
    )
    dev_env_block = parse_dev_env_workflow_block(
        repo_root, workflow_profile, config_materializer=mat
    )
    memory_meta = memory_effective_metadata(mem_block, run_policy_overrides=run_policy_overrides)
    memory_index_version = resolve_memory_index_version(memory_chunk_store, repo_root=repo_root)
    if memory_index_version:
        memory_meta["memory_index_version"] = memory_index_version
    return CreateRunWorkflowBlocks(
        uc_block=uc_block,
        uc_eff=uc_eff,
        ae_block=ae_block,
        sr_block=sr_block,
        prob_block=prob_block,
        fs_block=fs_block,
        patch_block=patch_block,
        campaign_block=campaign_block,
        backlog_block=backlog_block,
        maintenance_block=maintenance_block,
        completion_block=completion_block,
        ms_block=ms_block,
        mem_block=mem_block,
        research_block=research_block,
        stitch_block=stitch_block,
        theater_block=theater_block,
        dev_env_block=dev_env_block,
        memory_meta=memory_meta,
    )
