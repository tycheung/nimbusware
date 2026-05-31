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
from nimbusware_console.integrator_workflow_preview import (
    parse_integrator_gate_yaml_fragment,
    preview_effective_min_score_to_pass,
)
from hermes_orchestrator.integrator_gate import (
    effective_integrator_min_score_to_pass,
    integrator_gate_workflow_enabled,
    load_integrator_gate_emit_enabled,
    load_integrator_gate_workflow_block,
    parse_integrator_gate_min_score_to_pass,
    parse_integrator_gate_project_tags,
)
from nimbusware_config.workflow_read import (
    load_yaml,
    workflow_profile_path,
)
from nimbusware_console.components.workflow_explainer_helpers import relative_under

from nimbusware_console.integrator_threshold_explainer.snapshots import (
    _emit_integrator_gate_breakdown,
    _env_min_score_to_pass_breakdown,
    _thresholds_snapshot,
)
def integrator_threshold_explainer_payload(
    repo_root: Path,
    *,
    workflow_profile: str | None,
    pasted_yaml: str,
) -> dict[str, Any]:
    wf_key = str(workflow_profile).strip() if workflow_profile else ""
    wf_sel: str | None = wf_key if wf_key else None

    pasted_block, paste_errs = parse_integrator_gate_yaml_fragment(pasted_yaml)

    mat = console_config_materializer(repo_root)

    workflow_yaml_relpath: str | None = None
    if wf_sel:
        try:
            if mat is not None:
                workflow_yaml_relpath = f"configs/workflows/{wf_sel}.yaml"
            else:
                wp = workflow_profile_path(repo_root, wf_sel)
                workflow_yaml_relpath = relative_under(repo_root, wp)
        except (FileNotFoundError, OSError, ValueError):
            workflow_yaml_relpath = None

    wf_block = load_integrator_gate_workflow_block(
        repo_root,
        wf_sel,
        config_materializer=mat,
    )
    wf_min = parse_integrator_gate_min_score_to_pass(
        repo_root,
        wf_sel,
        config_materializer=mat,
    )
    wf_tags = parse_integrator_gate_project_tags(
        repo_root,
        wf_sel,
        config_materializer=mat,
    )
    wf_project_tags_count: int | None = None
    if isinstance(wf_block, dict):
        raw_tags = wf_block.get("project_tags")
        if isinstance(raw_tags, list):
            wf_project_tags_count = len(raw_tags)

    pipe_eff = effective_integrator_min_score_to_pass(
        repo_root,
        wf_sel,
        config_materializer=mat,
    )
    preview_eff = preview_effective_min_score_to_pass(repo_root, wf_sel, pasted_block)

    note = (
        "Streamlit preview uses pasted min_score_to_pass before workflow when the pasted "
        "fragment parses; pipeline emission uses env, then workflow, then thresholds.yaml only."
    )
    if preview_eff == pipe_eff:
        note = (
            "Preview and pipeline agree on min score (no pasted override, or same numeric result)."
        )

    return {
        "workflow_profile": wf_sel,
        "workflow_yaml_relpath": workflow_yaml_relpath,
        "paste_parse_errors": list(paste_errs),
        "pasted_min_score_in_fragment": (
            pasted_block.get("min_score_to_pass") if isinstance(pasted_block, dict) else None
        ),
        "thresholds_yaml": _thresholds_snapshot(repo_root, config_materializer=mat),
        "workflow_integrator_gate": {
            "block_present": wf_block is not None,
            "enabled": bool(wf_block.get("enabled")) if wf_block else None,
            "min_score_to_pass": wf_min,
            "project_tags": wf_tags,
            "project_tags_list_length": wf_project_tags_count,
        },
        "env_min_score_to_pass": _env_min_score_to_pass_breakdown(),
        "pipeline_effective_min_score_to_pass": pipe_eff,
        "streamlit_preview_effective_min_score_to_pass": preview_eff,
        "min_score_agreement_note": note,
        "gate_event_emission": _emit_integrator_gate_breakdown(
            repo_root,
            wf_sel,
            config_materializer=mat,
        ),
    }


