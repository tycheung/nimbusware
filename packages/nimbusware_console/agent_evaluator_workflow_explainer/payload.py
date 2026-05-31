from __future__ import annotations

from nimbusware_console.components.operator_metrics import (
    FIELD_VALUE_COLUMNS,
    field_value_table_rows_csv,
    mapping_export_json,
    mapping_to_sorted_table_rows,
    sequence_export_json,
    table_rows_csv,
)
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from nimbusware_console.config_materializer import console_config_materializer
from nimbusware_console.explainer_workflow_disk import load_workflow_profile_documents
from nimbusware_config.workflow_read import parse_agent_evaluator_workflow_block
from nimbusware_console.components.workflow_explainer_helpers import (
    json_safe_yaml_fragment,
    relative_under,
)

from nimbusware_console.agent_evaluator_workflow_explainer.env import (
    _hermes_agent_evaluator_auto_create_env_summary,
    _hermes_agent_evaluator_auto_promote_env_summary,
    _hermes_agent_evaluator_env_summary,
    _would_emit_agent_evaluator_stage,
    _would_emit_llm_evaluation,
)
def agent_evaluator_workflow_explainer_payload(
    repo_root: Path,
    *,
    workflow_profile: str | None,
) -> dict[str, Any]:
    wf_key = str(workflow_profile).strip() if workflow_profile else ""
    wf_sel: str | None = wf_key if wf_key else None

    workflow_yaml_relpath: str | None = None
    load_error: str | None = None
    yaml_key_present = False
    yaml_value: Any = None
    workflow_yaml_top_level_version_int: int | None = None

    mat = console_config_materializer(repo_root)
    if wf_sel:
        try:
            disk_doc, _effective_doc, wp, _file_bytes = load_workflow_profile_documents(
                repo_root,
                wf_sel,
                materializer=mat,
            )
            workflow_yaml_relpath = relative_under(repo_root, wp)
            doc = disk_doc
            if isinstance(doc, dict):
                vtop = doc.get("version")
                if type(vtop) is int and not isinstance(vtop, bool):
                    workflow_yaml_top_level_version_int = vtop
                if "agent_evaluator" in doc:
                    yaml_key_present = True
                    yaml_value = doc.get("agent_evaluator")
        except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError) as err:
            load_error = str(err)
            yaml_value = None

    block = parse_agent_evaluator_workflow_block(
        repo_root,
        wf_sel,
        config_materializer=mat,
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
    if isinstance(yaml_value, dict):
        yaml_mapping_string_key_count = sum(1 for k in yaml_value if isinstance(k, str))
        yaml_true_bool_value_count = sum(
            1 for v in yaml_value.values() if type(v) is bool and v is True
        )
        yaml_false_bool_value_count = sum(
            1 for v in yaml_value.values() if type(v) is bool and v is False
        )

    ac = block.auto_create_persona
    return {
        "workflow_profile": wf_sel,
        "workflow_yaml_relpath": workflow_yaml_relpath,
        "workflow_yaml_top_level_version_int": workflow_yaml_top_level_version_int,
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
        "HERMES_AGENT_EVALUATOR": _hermes_agent_evaluator_env_summary(),
        "HERMES_AGENT_EVALUATOR_AUTO_PROMOTE": _hermes_agent_evaluator_auto_promote_env_summary(),
        "HERMES_AGENT_EVALUATOR_AUTO_CREATE": _hermes_agent_evaluator_auto_create_env_summary(),
        "would_emit_stage_started": would_emit,
        "would_emit_llm_evaluation": would_emit_llm,
        "load_error": load_error,
    }


