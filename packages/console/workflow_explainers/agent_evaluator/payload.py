from __future__ import annotations

from pathlib import Path
from typing import Any

from config.workflow_read import parse_agent_evaluator_workflow_block
from console.explainer_core.env_summaries import (
    env_disable_flag_summary,
    env_tri_state_summary,
)
from console.explainer_core.repo_yaml import json_safe_yaml_fragment
from console.explainer_core.workflow_payload_header import workflow_payload_header
from console.explainer_core.workflow_profile import yaml_section
from env.env_flags import nimbusware_use_llm_enabled
from orchestrator.workflow.agent_evaluator import agent_evaluator_stage_would_emit


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


def agent_evaluator_workflow_explainer_payload(
    repo_root: Path,
    *,
    workflow_profile: str | None,
) -> dict[str, Any]:
    snap, header = workflow_payload_header(repo_root, workflow_profile)
    wf_sel = snap.workflow_profile
    yaml_key_present = "agent_evaluator" in snap.disk_doc
    yaml_value = snap.disk_doc.get("agent_evaluator") if yaml_key_present else None

    block = parse_agent_evaluator_workflow_block(
        repo_root,
        wf_sel,
        config_materializer=snap.materializer,
    )
    would_emit = _would_emit_agent_evaluator_stage(repo_root, wf_sel)
    would_emit_llm = _would_emit_llm_evaluation(repo_root, wf_sel)

    yaml_raw_type: str | None
    if yaml_value is None:
        yaml_raw_type = None
    else:
        yaml_raw_type = type(yaml_value).__name__

    yaml_mapping_string_key_count: int | None = None
    yaml_true_bool_value_count: int | None = None
    yaml_false_bool_value_count: int | None = None
    section = yaml_section(snap.disk_doc, "agent_evaluator")
    if section:
        yaml_mapping_string_key_count = sum(1 for k in section if isinstance(k, str))
        yaml_true_bool_value_count = sum(
            1 for v in section.values() if type(v) is bool and v is True
        )
        yaml_false_bool_value_count = sum(
            1 for v in section.values() if type(v) is bool and v is False
        )

    ac = block.auto_create_persona
    return {
        **header,
        "agent_evaluator_yaml_key_present": yaml_key_present,
        "agent_evaluator_yaml_value": json_safe_yaml_fragment(yaml_value),
        "agent_evaluator_yaml_raw_type": yaml_raw_type,
        "agent_evaluator_yaml_mapping_string_key_count": yaml_mapping_string_key_count,
        "agent_evaluator_yaml_true_bool_value_count": yaml_true_bool_value_count,
        "agent_evaluator_yaml_false_bool_value_count": yaml_false_bool_value_count,
        "yaml_parsed_enabled": block.enabled,
        "yaml_parsed_llm_evaluation_enabled": block.llm_evaluation_enabled,
        "yaml_parsed_persona_id": block.persona_id,
        "yaml_parsed_auto_promote_probation": block.auto_promote_probation,
        "yaml_parsed_auto_create_persona": {
            "enabled": ac.enabled,
            "shelf": ac.shelf,
            "display_name": ac.display_name,
        },
        "NIMBUSWARE_AGENT_EVALUATOR": _nimbusware_agent_evaluator_env_summary(),
        "NIMBUSWARE_AGENT_EVALUATOR_AUTO_PROMOTE": _nimbusware_agent_evaluator_auto_promote_env_summary(),
        "NIMBUSWARE_AGENT_EVALUATOR_AUTO_CREATE": _nimbusware_agent_evaluator_auto_create_env_summary(),
        "would_emit_stage_started": would_emit,
        "would_emit_llm_evaluation": would_emit_llm,
    }
