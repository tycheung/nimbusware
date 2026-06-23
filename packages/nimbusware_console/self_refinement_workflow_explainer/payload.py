from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from nimbusware_config.workflow_read import (
    parse_self_refinement_workflow_block,
)
from nimbusware_console.explainer_core.workflow_payload_header import workflow_payload_header
from nimbusware_console.explainer_core.workflow_profile import yaml_section
from nimbusware_console.self_refinement_workflow_explainer.env import (
    _load_policy_or_default,
    _marker_preview,
    _nimbusware_self_refinement_ungated_loop_env_summary,
)


def self_refinement_workflow_explainer_payload(
    repo_root: Path,
    *,
    workflow_profile: str | None,
) -> dict[str, Any]:
    snap, header = workflow_payload_header(repo_root, workflow_profile)
    wf_sel = snap.workflow_profile
    block = snap.disk_doc.get("self_refinement")
    sr_workflow_yaml_raw_type = type(block).__name__ if block is not None else None
    section = yaml_section(snap.disk_doc, "self_refinement")
    sr_yaml_mapping_string_key_count = (
        sum(1 for k in section if isinstance(k, str)) if section else None
    )
    sr_present = bool(section)

    wf_sr = parse_self_refinement_workflow_block(
        repo_root,
        wf_sel,
        config_materializer=snap.materializer,
    )
    pol, pol_snap = _load_policy_or_default(repo_root, config_materializer=snap.materializer)
    pol_snap["enabled"] = pol.enabled
    pol_snap["version"] = pol.version
    pol_snap["description"] = pol.description
    pol_snap["description_char_len"] = len(pol.description or "")

    marker = _marker_preview(wf_sr, pol)

    return {
        **header,
        "self_refinement_yaml_present": sr_present,
        "self_refinement_workflow_yaml_raw_type": sr_workflow_yaml_raw_type,
        "self_refinement_yaml_mapping_string_key_count": sr_yaml_mapping_string_key_count,
        "workflow_self_refinement": asdict(wf_sr),
        "policy_yaml": pol_snap,
        "marker_merge": marker,
        "NIMBUSWARE_SELF_REFINEMENT_UNGATED_LOOP": _nimbusware_self_refinement_ungated_loop_env_summary(),
    }
