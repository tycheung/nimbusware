from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from nimbusware_agent_tools.filesystem_jail import default_jail_policy
from nimbusware_agent_tools.risk_caps import PATCH_DEFAULT_CAPS, resolve_agent_risk_caps
from nimbusware_agent_tools.sandbox import resolve_sandbox_backend
from nimbusware_hw.cache import get_cached_profile
from nimbusware_hw.governor import governor_for_profile
from nimbusware_orchestrator._pipeline._helpers import (
    agent_evaluator_production_default_on,
    self_refinement_production_ungated_effective,
    self_refinement_ungated_loop_effective,
    universal_critique_production_default_on,
)
from nimbusware_orchestrator._pipeline.create_run_workflow_blocks import CreateRunWorkflowBlocks
from nimbusware_orchestrator.autopilot_profiles import autopilot_effective_metadata
from nimbusware_orchestrator.critic_pack_resolve import resolve_critic_pack_for_workflow
from nimbusware_orchestrator.enforcement_profiles import enforcement_effective_metadata
from nimbusware_orchestrator.patch_context import normalize_patch_context
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.slice_budget_presets import resolve_slice_budget_preset
from nimbusware_orchestrator.workflow_campaign import campaign_effective_metadata
from nimbusware_orchestrator.workflow_dev_env import dev_env_effective_metadata
from nimbusware_orchestrator.workflow_fast_slice import fast_slice_effective_metadata
from nimbusware_orchestrator.workflow_patch import patch_effective_metadata
from nimbusware_orchestrator.workflow_probation_automation import (
    probation_automation_effective_metadata,
)
from nimbusware_orchestrator.workflow_research import (
    research_effective_metadata,
    stitch_effective_metadata,
)
from nimbusware_orchestrator.workflow_theater import theater_effective_metadata


def resolve_custom_agent_meta(
    repo_root: Path,
    custom_agent_id: str | None,
    *,
    config_materializer: Any | None,
) -> dict[str, Any] | None:
    if not custom_agent_id or not str(custom_agent_id).strip():
        return None
    from nimbusware_config.persist import load_custom_agent_registry

    reg = load_custom_agent_registry(repo_root, materializer=config_materializer)
    agent = reg.get(str(custom_agent_id).strip())
    if agent is None:
        raise ValueError(f"Unknown custom_agent_id: {custom_agent_id}")
    return {
        "id": agent.id,
        "display_name": agent.display_name,
        "system_prompt_preview": agent.system_prompt[:240],
        "bound_role_id": agent.bound_role_id,
    }


def resolve_project_meta(
    project_id: UUID | None,
    *,
    project_name: str | None,
    project_workspace_path: str | None,
    project_template: str | None,
) -> dict[str, Any] | None:
    if project_id is None:
        return None
    if not project_workspace_path or not str(project_workspace_path).strip():
        raise ValueError("project_workspace_path required when project_id is set")
    ws = Path(str(project_workspace_path)).resolve()
    if not ws.is_dir():
        raise ValueError(f"project workspace_path is not a directory: {ws}")
    return {
        "id": str(project_id),
        "name": (project_name or "").strip() or str(project_id),
        "workspace_path": str(ws),
        "template": (project_template or "attach").strip() or "attach",
    }


def resolve_requirements_meta(requirements: dict[str, Any] | None) -> dict[str, Any] | None:
    if requirements is None:
        return None
    if (
        not isinstance(requirements, dict)
        or not str(requirements.get("business_prompt", "")).strip()
    ):
        raise ValueError("requirements.business_prompt required when requirements is set")
    return dict(requirements)


def build_run_created_metadata(
    *,
    registry: RoleRegistry,
    repo_root: Path,
    workflow_profile: str,
    config_materializer: Any | None,
    blocks: CreateRunWorkflowBlocks,
    critique_coverage: dict[str, Any],
    stage_graph_snapshot: dict[str, Any],
    snapshot: Any,
    run_policy_overrides: dict[str, Any] | None,
    custom_agent_meta: dict[str, Any] | None,
    project_meta: dict[str, Any] | None,
    requirements_meta: dict[str, Any] | None,
    operator_settings_meta: dict[str, str] | None,
    autonomous: bool | None,
    patch_context: dict[str, Any] | None,
    work_type: str | None,
    work_type_source: str | None,
    business_area_persona_id: str | None,
    development_role_persona_id: str | None,
) -> dict[str, Any]:
    mat = config_materializer
    uc_block = blocks.uc_block
    uc_eff = blocks.uc_eff
    ae_block = blocks.ae_block
    sr_block = blocks.sr_block
    memory_meta = blocks.memory_meta
    universal_critique_effective = {
        "default_enabled": uc_block.default_enabled,
        "production_default_on": universal_critique_production_default_on(
            repo_root, workflow_profile, config_materializer=mat
        ),
        "impl_llm": uc_eff.impl_llm,
        "impl_stub": uc_eff.impl_stub,
        "tw_enabled": uc_eff.tw_enabled,
        "pll_enabled": uc_eff.pll_enabled,
        "fw_enabled": uc_eff.fw_enabled,
        "mi_enabled": uc_eff.mi_enabled,
        "unanimous_gate_enforce": uc_eff.unanimous_gate_enforce,
    }
    agent_evaluator_effective = {
        "enabled": ae_block.enabled,
        "production_default_on": agent_evaluator_production_default_on(
            repo_root, workflow_profile, config_materializer=mat
        ),
        "llm_evaluation_enabled": ae_block.llm_evaluation_enabled,
    }
    self_refinement_effective = {
        "enabled": sr_block.enabled,
        "ungated_loop": self_refinement_ungated_loop_effective(sr_block),
        "production_ungated": self_refinement_production_ungated_effective(
            repo_root, workflow_profile, config_materializer=mat
        ),
        "llm_critique_enabled": sr_block.llm_critique_enabled,
    }
    hw_profile = get_cached_profile()
    resource_governor = governor_for_profile(hw_profile).to_metadata()
    patch_block = blocks.patch_block
    risk_caps = resolve_agent_risk_caps()
    if patch_block.enabled and patch_block.risk_caps is not None:
        risk_caps = patch_block.risk_caps
    elif patch_block.enabled:
        risk_caps = PATCH_DEFAULT_CAPS
    agent_tools_effective = {
        "sandbox_backend": resolve_sandbox_backend(),
        "filesystem_jail": default_jail_policy().enabled,
        "risk_caps": risk_caps.to_metadata(),
    }
    slice_budget = resolve_slice_budget_preset(operator_settings=operator_settings_meta)
    ms_block = blocks.ms_block
    ms_max_files = ms_block.max_files
    ms_max_loc = ms_block.max_loc
    if ms_block.enabled:
        ms_max_files = slice_budget.max_files
        ms_max_loc = slice_budget.max_loc
    critic_pack_effective = resolve_critic_pack_for_workflow(
        repo_root, workflow_profile, config_materializer=mat
    )
    campaign_block = blocks.campaign_block
    campaign_meta = (
        campaign_effective_metadata(
            campaign_block,
            blocks.backlog_block,
            blocks.maintenance_block,
            blocks.completion_block,
            autonomous=autonomous,
        )
        if campaign_block.enabled
        else None
    )
    patch_ctx_norm = normalize_patch_context(patch_context)
    git_meta: dict[str, Any] | None = None
    if project_meta and str(work_type or "").strip().lower() in {"campaign", "factory"}:
        ws_git = Path(str(project_meta["workspace_path"]))
        if (ws_git / ".git").is_dir():
            git_meta = {"native_outputs": True, "open_pr_on_complete": True}
    wt = str(work_type or "").strip().lower() or None
    if patch_block.enabled and not wt:
        wt = "patch"
    wts = str(work_type_source or "").strip().lower() or None
    is_patch_run = patch_block.enabled or wt == "patch"
    return {
        "roles_registry": {
            "yaml_version": registry.yaml_version,
            "content_digest_sha256_16": registry.content_digest_sha256_16,
        },
        "policy_snapshot": {
            "domain_allowlist_normalized": True,
            "network_egress_domain_count": len(snapshot.network_egress.domain_allowlist),
        },
        "hardware_profile": hw_profile.model_dump_public(),
        "resource_governor": resource_governor,
        "critique_coverage": critique_coverage,
        "stage_graph": stage_graph_snapshot,
        "universal_critique_effective": universal_critique_effective,
        **({"critic_pack_effective": critic_pack_effective} if critic_pack_effective else {}),
        "agent_evaluator_effective": agent_evaluator_effective,
        "self_refinement_effective": self_refinement_effective,
        "probation_automation_effective": probation_automation_effective_metadata(
            blocks.prob_block
        ),
        "fast_slice_effective": fast_slice_effective_metadata(blocks.fs_block),
        "micro_slice_effective": {
            "enabled": True,
            "max_files": ms_max_files,
            "max_loc": ms_max_loc,
            "e2e_enabled": ms_block.e2e_enabled,
            "budget_preset": slice_budget.name,
            "replan_max": slice_budget.replan_max,
            "one_at_a_time": campaign_block.enabled,
        },
        **({"campaign_effective": campaign_meta} if campaign_meta else {}),
        **(
            {"patch_effective": patch_effective_metadata(patch_block)}
            if patch_block.enabled
            else {}
        ),
        **({"patch_context": patch_ctx_norm} if patch_ctx_norm else {}),
        **({"work_type": wt} if wt else {}),
        **({"work_type_source": wts} if wts else {}),
        **({"autopilot_effective": autopilot_effective_metadata(wt)} if wt else {}),
        **({"enforcement_effective": enforcement_effective_metadata(wt)} if wt else {}),
        "agent_tools_effective": agent_tools_effective,
        "memory_effective": {
            "retrieval_enabled": memory_meta["retrieval_enabled"],
            "index_contribution": memory_meta["index_contribution"],
            "retrieval_k": memory_meta["retrieval_k"],
            "excerpt_max_chars": memory_meta["excerpt_max_chars"],
            "embedding_mode": memory_meta["embedding_mode"],
            "memory_index_version": memory_meta.get("memory_index_version"),
        },
        "memory": memory_meta,
        "research": research_effective_metadata(blocks.research_block),
        "stitch": stitch_effective_metadata(blocks.stitch_block),
        "theater": theater_effective_metadata(blocks.theater_block),
        "dev_env_effective": dev_env_effective_metadata(blocks.dev_env_block),
        **({"custom_agent": custom_agent_meta} if custom_agent_meta else {}),
        **({"project": project_meta} if project_meta else {}),
        **({"git": git_meta} if git_meta else {}),
        **({"requirements": requirements_meta} if requirements_meta else {}),
        **({"operator_settings": operator_settings_meta} if operator_settings_meta else {}),
        **(
            {"maker_approval": {"enabled": True}}
            if requirements_meta is not None
            and not (isinstance(campaign_meta, dict) and campaign_meta.get("autonomous"))
            and not is_patch_run
            else {}
        ),
        **(
            {
                "persona_assignment": {
                    "business_area": (
                        str(business_area_persona_id).strip() if business_area_persona_id else None
                    ),
                    "development_role": (
                        str(development_role_persona_id).strip()
                        if development_role_persona_id
                        else None
                    ),
                },
            }
            if business_area_persona_id or development_role_persona_id
            else {}
        ),
    }
