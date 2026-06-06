"""Parse workflow ``campaign`` / ``backlog`` / ``maintenance`` / ``completion`` blocks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from agent_core.models.backlog import CampaignPolicy
from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict


@dataclass(frozen=True)
class CampaignWorkflowBlock:
    enabled: bool = False
    autonomous_default: bool = True
    tick_idle_seconds: float = 2.0
    max_consecutive_failures: int = 5


@dataclass(frozen=True)
class BacklogWorkflowBlock:
    generator: Literal["stub", "llm"] = "stub"
    max_slices: int = 500
    require_backlog_approval: bool = False


@dataclass(frozen=True)
class MaintenanceWorkflowBlock:
    refactor_every_n_slices: int = 5
    architecture_every_n_slices: int = 10
    refactor_inserts_fix_slices: bool = True
    architecture_can_revise_backlog: bool = True


@dataclass(frozen=True)
class CompletionWorkflowBlock:
    require_project_tests_pass: bool = True
    require_all_must_have_features: bool = True
    deep_eval_every_n_slices: int = 20


def parse_campaign_workflow_block(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
) -> CampaignWorkflowBlock:
    wf = workflow_profile_dict(repo_root, workflow_profile, materializer=config_materializer)
    raw = wf.get("campaign")
    if not isinstance(raw, dict):
        return CampaignWorkflowBlock()
    driver = raw.get("driver")
    tick_idle = 2.0
    max_failures = 5
    if isinstance(driver, dict):
        tick_idle = float(driver.get("tick_idle_seconds", 2) or 2)
        max_failures = int(driver.get("max_consecutive_failures", 5) or 5)
    return CampaignWorkflowBlock(
        enabled=bool(raw.get("enabled", False)),
        autonomous_default=bool(raw.get("autonomous_default", True)),
        tick_idle_seconds=max(0.0, tick_idle),
        max_consecutive_failures=max(1, max_failures),
    )


def parse_backlog_workflow_block(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
) -> BacklogWorkflowBlock:
    wf = workflow_profile_dict(repo_root, workflow_profile, materializer=config_materializer)
    raw = wf.get("backlog")
    if not isinstance(raw, dict):
        return BacklogWorkflowBlock()
    gen = str(raw.get("generator", "stub")).strip().lower()
    if gen not in ("stub", "llm"):
        gen = "stub"
    return BacklogWorkflowBlock(
        generator=gen,  # type: ignore[arg-type]
        max_slices=max(1, int(raw.get("max_slices", 500) or 500)),
        require_backlog_approval=bool(raw.get("require_backlog_approval", False)),
    )


def parse_maintenance_workflow_block(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
) -> MaintenanceWorkflowBlock:
    wf = workflow_profile_dict(repo_root, workflow_profile, materializer=config_materializer)
    raw = wf.get("maintenance")
    if not isinstance(raw, dict):
        return MaintenanceWorkflowBlock()
    return MaintenanceWorkflowBlock(
        refactor_every_n_slices=max(1, int(raw.get("refactor_every_n_slices", 5) or 5)),
        architecture_every_n_slices=max(1, int(raw.get("architecture_every_n_slices", 10) or 10)),
        refactor_inserts_fix_slices=bool(raw.get("refactor_inserts_fix_slices", True)),
        architecture_can_revise_backlog=bool(raw.get("architecture_can_revise_backlog", True)),
    )


def parse_completion_workflow_block(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
) -> CompletionWorkflowBlock:
    wf = workflow_profile_dict(repo_root, workflow_profile, materializer=config_materializer)
    raw = wf.get("completion")
    if not isinstance(raw, dict):
        return CompletionWorkflowBlock()
    return CompletionWorkflowBlock(
        require_project_tests_pass=bool(raw.get("require_project_tests_pass", True)),
        require_all_must_have_features=bool(
            raw.get("require_all_must_have_features", True),
        ),
        deep_eval_every_n_slices=max(1, int(raw.get("deep_eval_every_n_slices", 20) or 20)),
    )


def campaign_policy_from_blocks(
    campaign: CampaignWorkflowBlock,
    backlog: BacklogWorkflowBlock,
    maintenance: MaintenanceWorkflowBlock,
    completion: CompletionWorkflowBlock,
    *,
    autonomous: bool | None = None,
) -> CampaignPolicy:
    return CampaignPolicy(
        autonomous=autonomous if autonomous is not None else campaign.autonomous_default,
        max_slices=backlog.max_slices,
        refactor_every_n_slices=maintenance.refactor_every_n_slices,
        architecture_every_n_slices=maintenance.architecture_every_n_slices,
        deep_eval_every_n_slices=completion.deep_eval_every_n_slices,
        tick_idle_seconds=campaign.tick_idle_seconds,
        backlog_generator=backlog.generator,
        require_backlog_approval=backlog.require_backlog_approval,
        max_consecutive_slice_failures=campaign.max_consecutive_failures,
    )


def campaign_effective_metadata(
    campaign: CampaignWorkflowBlock,
    backlog: BacklogWorkflowBlock,
    maintenance: MaintenanceWorkflowBlock,
    completion: CompletionWorkflowBlock,
    *,
    autonomous: bool | None = None,
) -> dict[str, Any]:
    policy = campaign_policy_from_blocks(
        campaign,
        backlog,
        maintenance,
        completion,
        autonomous=autonomous,
    )
    return {
        "enabled": campaign.enabled,
        "autonomous": policy.autonomous,
        "policy": policy.model_dump(mode="json"),
        "maintenance": {
            "refactor_inserts_fix_slices": maintenance.refactor_inserts_fix_slices,
            "architecture_can_revise_backlog": maintenance.architecture_can_revise_backlog,
        },
        "completion": {
            "require_project_tests_pass": completion.require_project_tests_pass,
            "require_all_must_have_features": completion.require_all_must_have_features,
        },
    }
