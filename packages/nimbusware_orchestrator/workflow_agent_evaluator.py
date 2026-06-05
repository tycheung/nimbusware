"""Workflow YAML knobs for agent evaluator ``stage.started`` marker ."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nimbusware_env.env_flags import (
    env_falsy,
    env_tri_state,
    env_truthy,
    nimbusware_use_llm_explicitly_off,
)
from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict


@dataclass(frozen=True)
class PersonaCoverageCritiqueBlock:
    enabled: bool = False
    stub: bool = True
    llm_enabled: bool = False


@dataclass(frozen=True)
class AgentEvaluatorAutoCreatePersonaBlock:
    """Optional ``agent_evaluator.auto_create_persona`` subtree (declarative create-if-missing)."""

    enabled: bool = False
    shelf: str = ""
    display_name: str = ""


@dataclass(frozen=True)
class AgentEvaluatorWorkflowBlock:
    """Parsed ``agent_evaluator`` subsection from ``configs/workflows/{profile}.yaml``."""

    enabled: bool = False
    persona_id: str = "default"
    llm_evaluation_enabled: bool = False
    auto_promote_probation: bool = False
    auto_create_persona: AgentEvaluatorAutoCreatePersonaBlock = field(
        default_factory=AgentEvaluatorAutoCreatePersonaBlock,
    )
    persona_coverage_critique: PersonaCoverageCritiqueBlock = field(
        default_factory=PersonaCoverageCritiqueBlock,
    )


def parse_agent_evaluator_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> AgentEvaluatorWorkflowBlock:
    """Return workflow agent_evaluator overrides; missing block → ``enabled=False``, ``default``."""
    if workflow_profile is None or not str(workflow_profile).strip():
        return AgentEvaluatorWorkflowBlock()
    key = str(workflow_profile).strip()
    try:
        raw = workflow_profile_dict(repo_root, key, materializer=config_materializer)
    except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError):
        return AgentEvaluatorWorkflowBlock()
    block = raw.get("agent_evaluator")
    if not isinstance(block, dict):
        return AgentEvaluatorWorkflowBlock()
    enabled = bool(block.get("enabled", False))
    persona_raw = block.get("persona_id", "default")
    persona_id = str(persona_raw).strip() if persona_raw is not None else "default"
    if not persona_id:
        persona_id = "default"
    auto_promote = bool(block.get("auto_promote_probation", False))
    llm_eval = bool(block.get("llm_evaluation_enabled", False))

    ac_raw = block.get("auto_create_persona")
    ac_enabled = False
    ac_shelf = ""
    ac_display = ""
    if isinstance(ac_raw, dict):
        ac_enabled = bool(ac_raw.get("enabled", False))
        shelf_raw = ac_raw.get("shelf")
        ac_shelf = str(shelf_raw).strip() if shelf_raw is not None else ""
        dn_raw = ac_raw.get("display_name")
        ac_display = str(dn_raw).strip() if dn_raw is not None else ""
    ac_block = AgentEvaluatorAutoCreatePersonaBlock(
        enabled=ac_enabled,
        shelf=ac_shelf,
        display_name=ac_display,
    )

    pcc_raw = block.get("persona_coverage_critique")
    pcc_enabled = False
    pcc_stub = True
    if isinstance(pcc_raw, dict):
        pcc_enabled = bool(pcc_raw.get("enabled", False))
        pcc_stub = bool(pcc_raw.get("stub", True))
    pcc_llm = bool(pcc_raw.get("llm_enabled", False)) if isinstance(pcc_raw, dict) else False
    pcc_block = PersonaCoverageCritiqueBlock(
        enabled=pcc_enabled,
        stub=pcc_stub,
        llm_enabled=pcc_llm,
    )

    return AgentEvaluatorWorkflowBlock(
        enabled=enabled,
        persona_id=persona_id,
        llm_evaluation_enabled=llm_eval,
        auto_promote_probation=auto_promote,
        auto_create_persona=ac_block,
        persona_coverage_critique=pcc_block,
    )


def persona_coverage_critique_effective(block: AgentEvaluatorWorkflowBlock) -> bool:
    """Env ``NIMBUSWARE_PERSONA_COVERAGE_CRITIQUE=0`` kill-switch overrides workflow YAML."""
    tri = env_tri_state("NIMBUSWARE_PERSONA_COVERAGE_CRITIQUE")
    if tri == "off":
        return False
    if tri == "on":
        return True
    return block.persona_coverage_critique.enabled


def agent_evaluator_llm_stub_env_enabled() -> bool:
    return env_truthy("NIMBUSWARE_AGENT_EVALUATOR_LLM_STUB")


def agent_evaluator_rules_derived_llm_evaluation(rules_eval: dict[str, Any]) -> dict[str, Any]:
    """Production fallback when YAML authorizes LLM but runtime LLM is unavailable."""
    gaps = rules_eval.get("gaps")
    return {
        "status": str(rules_eval.get("status", "ok")),
        "gaps": list(gaps) if isinstance(gaps, list) else [],
        "summary": "rules-derived evaluator policy (production fallback)",
        "production_scoring_mode": "rules_derived",
    }


def agent_evaluator_production_llm_fallback_enabled(
    block: AgentEvaluatorWorkflowBlock,
) -> bool:
    return agent_evaluator_llm_branch_effective(block) and not (
        agent_evaluator_llm_stub_env_enabled()
    )


def agent_evaluator_production_default_on(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> bool:
    """True when YAML enables evaluator + LLM branch and no production kill-switch is set."""
    block = parse_agent_evaluator_workflow_block(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    if not block.enabled or not block.llm_evaluation_enabled:
        return False
    if env_falsy("NIMBUSWARE_AGENT_EVALUATOR"):
        return False
    if nimbusware_use_llm_explicitly_off():
        return False
    if agent_evaluator_llm_stub_env_enabled():
        return False
    return True


def agent_evaluator_llm_branch_effective(block: AgentEvaluatorWorkflowBlock) -> bool:
    """YAML ``llm_evaluation_enabled`` suffices unless ``NIMBUSWARE_USE_LLM`` is explicitly off."""
    if not block.llm_evaluation_enabled:
        return False
    if nimbusware_use_llm_explicitly_off():
        return False
    return True


def persona_coverage_critique_llm_branch_effective(
    block: AgentEvaluatorWorkflowBlock,
) -> bool:
    """Persona-coverage LLM when YAML enables it; ``NIMBUSWARE_USE_LLM=0`` still kill-switches."""
    if not persona_coverage_critique_llm_effective(block):
        return False
    if nimbusware_use_llm_explicitly_off():
        return False
    return True


def persona_coverage_critique_llm_effective(block: AgentEvaluatorWorkflowBlock) -> bool:
    tri = env_tri_state("NIMBUSWARE_PERSONA_COVERAGE_CRITIQUE_LLM")
    if tri == "off":
        return False
    if tri == "on":
        return True
    return block.persona_coverage_critique.llm_enabled
