from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from orchestrator._pipeline._helpers import effective_universal_critique
from orchestrator.workflow.memory import (
    memory_effective_metadata,
    resolve_memory_index_version,
)
from orchestrator.workflow.registry import parse_workflow_block

_CREATE_RUN_BLOCK_KEYS: tuple[str, ...] = (
    "universal_critique",
    "agent_evaluator",
    "self_refinement",
    "probation_automation",
    "fast_slice",
    "patch",
    "campaign",
    "backlog",
    "maintenance",
    "completion",
    "micro_slice",
    "memory",
    "research",
    "stitch",
    "theater",
    "dev_env",
)


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
    blocks = {
        key: parse_workflow_block(
            key,
            repo_root,
            workflow_profile,
            config_materializer=mat,
        )
        for key in _CREATE_RUN_BLOCK_KEYS
    }
    uc_eff = effective_universal_critique(repo_root, workflow_profile, config_materializer=mat)
    mem_block = blocks["memory"]
    memory_meta = memory_effective_metadata(mem_block, run_policy_overrides=run_policy_overrides)
    memory_index_version = resolve_memory_index_version(memory_chunk_store, repo_root=repo_root)
    if memory_index_version:
        memory_meta["memory_index_version"] = memory_index_version
    return CreateRunWorkflowBlocks(
        uc_block=blocks["universal_critique"],
        uc_eff=uc_eff,
        ae_block=blocks["agent_evaluator"],
        sr_block=blocks["self_refinement"],
        prob_block=blocks["probation_automation"],
        fs_block=blocks["fast_slice"],
        patch_block=blocks["patch"],
        campaign_block=blocks["campaign"],
        backlog_block=blocks["backlog"],
        maintenance_block=blocks["maintenance"],
        completion_block=blocks["completion"],
        ms_block=blocks["micro_slice"],
        mem_block=mem_block,
        research_block=blocks["research"],
        stitch_block=blocks["stitch"],
        theater_block=blocks["theater"],
        dev_env_block=blocks["dev_env"],
        memory_meta=memory_meta,
    )
