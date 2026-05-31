from __future__ import annotations

from nimbusware_console.components.operator_metrics import (
    FIELD_VALUE_COLUMNS,
    field_value_table_rows_csv,
    mapping_export_json,
    mapping_to_sorted_table_rows,
    sequence_export_json,
    table_rows_csv,
)
import csv
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from io import StringIO
from pathlib import Path
from typing import Any

from nimbusware_console.config_materializer import console_config_materializer
from nimbusware_console.explainer_workflow_disk import load_workflow_profile_documents
from hermes_extensions.self_refinement import (
    SelfRefinementPolicy,
    load_self_refinement_policy,
    self_refinement_policy_from_mapping,
)
from nimbusware_config.workflow_read import (
    SelfRefinementWorkflowBlock,
    load_yaml,
    parse_self_refinement_workflow_block,
    workflow_profile_dict,
    workflow_profile_path,
)
from nimbusware_console.components.workflow_explainer_helpers import relative_under

from nimbusware_console.self_refinement_workflow_explainer.env import (
    _hermes_self_refinement_ungated_loop_env_summary,
    _load_policy_or_default,
    _marker_preview,
)
def self_refinement_workflow_explainer_payload(
    repo_root: Path,
    *,
    workflow_profile: str | None,
) -> dict[str, Any]:
    wf_key = str(workflow_profile).strip() if workflow_profile else ""
    wf_sel: str | None = wf_key if wf_key else None

    mat = console_config_materializer(repo_root)

    workflow_yaml_relpath: str | None = None
    load_error: str | None = None
    sr_present = False
    sr_yaml_mapping_string_key_count: int | None = None
    sr_workflow_yaml_raw_type: str | None = None

    if wf_sel:
        try:
            disk_raw, _effective_raw, wp, _file_bytes = load_workflow_profile_documents(
                repo_root,
                wf_sel,
                materializer=mat,
            )
            workflow_yaml_relpath = relative_under(repo_root, wp)
            raw = disk_raw
            if isinstance(raw, dict) and "self_refinement" in raw:
                block = raw.get("self_refinement")
                if block is not None:
                    sr_workflow_yaml_raw_type = type(block).__name__
                if isinstance(block, dict):
                    sr_yaml_mapping_string_key_count = sum(
                        1 for k in block if isinstance(k, str)
                    )
                sr_present = isinstance(block, dict) and bool(block)
        except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError) as exc:
            load_error = str(exc)

    wf_sr = parse_self_refinement_workflow_block(
        repo_root,
        wf_sel,
        config_materializer=mat,
    )
    pol, pol_snap = _load_policy_or_default(repo_root, config_materializer=mat)
    pol_snap["enabled"] = pol.enabled
    pol_snap["version"] = pol.version
    pol_snap["description"] = pol.description
    pol_snap["description_char_len"] = len(pol.description or "")

    marker = _marker_preview(wf_sr, pol)

    return {
        "workflow_profile": wf_sel,
        "workflow_yaml_relpath": workflow_yaml_relpath,
        "load_error": load_error,
        "self_refinement_yaml_present": sr_present,
        "self_refinement_workflow_yaml_raw_type": sr_workflow_yaml_raw_type,
        "self_refinement_yaml_mapping_string_key_count": sr_yaml_mapping_string_key_count,
        "workflow_self_refinement": asdict(wf_sr),
        "policy_yaml": pol_snap,
        "marker_merge": marker,
        "HERMES_SELF_REFINEMENT_UNGATED_LOOP": _hermes_self_refinement_ungated_loop_env_summary(),
    }


