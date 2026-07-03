from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from env.env_flags import env_force_off, env_truthy_raw
from hw.governor import ResourceGovernor, governor_from_metadata
from orchestrator.workflow.parallel_writers import _coerce_yaml_bool
from orchestrator.workflow.profiles import workflow_profile_dict


@dataclass(frozen=True)
class ParallelCriticsWorkflowBlock:
    enabled: bool = False


def parse_parallel_critics_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> ParallelCriticsWorkflowBlock:
    if workflow_profile is None or not str(workflow_profile).strip():
        return ParallelCriticsWorkflowBlock()
    key = str(workflow_profile).strip()
    try:
        raw = workflow_profile_dict(repo_root, key, materializer=config_materializer)
    except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError):
        return ParallelCriticsWorkflowBlock()
    block = raw.get("parallel_critics")
    if not isinstance(block, dict):
        return ParallelCriticsWorkflowBlock()
    return ParallelCriticsWorkflowBlock(enabled=_coerce_yaml_bool(block.get("enabled")))


def _governor_from_resource_meta(
    resource_governor: dict[str, Any] | None,
) -> ResourceGovernor | None:
    if not isinstance(resource_governor, dict):
        return None
    if "resource_governor" in resource_governor:
        return governor_from_metadata(resource_governor)
    return governor_from_metadata({"resource_governor": resource_governor})


def parallel_critics_enabled(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    resource_governor: dict[str, Any] | None = None,
    config_materializer: Any | None = None,
) -> bool:
    if env_force_off("NIMBUSWARE_ALLOW_PARALLEL_CRITICS"):
        return False
    gov = _governor_from_resource_meta(resource_governor)
    tier = gov.hardware_tier if gov is not None else "medium"
    if tier != "strong":
        return False
    operator_on = env_truthy_raw("NIMBUSWARE_ALLOW_PARALLEL_CRITICS") or bool(
        gov and gov.allow_parallel_critics,
    )
    if not operator_on:
        return False
    wf = parse_parallel_critics_workflow_block(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    return wf.enabled or env_truthy_raw("NIMBUSWARE_ALLOW_PARALLEL_CRITICS")
