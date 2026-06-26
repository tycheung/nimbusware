from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_console.explainer_core.workflow_payload_header import workflow_payload_header
from nimbusware_console.integrator_workflow_preview import (
    parse_integrator_gate_yaml_fragment,
    preview_effective_min_score_to_pass,
)
from nimbusware_console.workflow_explainers.integrator_threshold.keys import (
    PREVIEW_EFFECTIVE_MIN_SCORE_KEY,
)
from nimbusware_console.workflow_explainers.integrator_threshold.snapshots import (
    _emit_integrator_gate_breakdown,
    _env_min_score_to_pass_breakdown,
    _thresholds_snapshot,
)
from nimbusware_orchestrator.integrator_gate import (
    effective_integrator_min_score_to_pass,
    load_integrator_gate_workflow_block,
    parse_integrator_gate_min_score_to_pass,
    parse_integrator_gate_project_tags,
)


def integrator_threshold_explainer_payload(
    repo_root: Path,
    *,
    workflow_profile: str | None,
    pasted_yaml: str,
) -> dict[str, Any]:
    snap, header = workflow_payload_header(repo_root, workflow_profile)
    wf_sel = snap.workflow_profile

    pasted_block, paste_errs = parse_integrator_gate_yaml_fragment(pasted_yaml)

    mat = snap.materializer

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
        "Admin preview uses pasted min_score_to_pass before workflow when the pasted "
        "fragment parses; pipeline emission uses env, then workflow, then thresholds.yaml only."
    )
    if preview_eff == pipe_eff:
        note = (
            "Preview and pipeline agree on min score (no pasted override, or same numeric result)."
        )

    return {
        **header,
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
        PREVIEW_EFFECTIVE_MIN_SCORE_KEY: preview_eff,
        "min_score_agreement_note": note,
        "gate_event_emission": _emit_integrator_gate_breakdown(
            repo_root,
            wf_sel,
            config_materializer=mat,
        ),
    }
