from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

from config.workflow_read import (
    SelfRefinementWorkflowBlock,
    load_yaml,
    parse_self_refinement_workflow_block,
)
from console.explainer_core.env_captions import env_tri_state_registry_caption
from console.explainer_core.env_summaries import (
    env_disable_flag_summary,
    env_tri_state_summary,
)
from console.explainer_core.workflow_payload_header import workflow_payload_header
from console.explainer_core.workflow_profile import yaml_section
from env.env_flags import (
    env_falsy,
    env_str,
)
from extensions.self_refinement import (
    SelfRefinementPolicy,
)


def _load_policy_or_default(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> tuple[SelfRefinementPolicy, dict[str, Any]]:
    from orchestrator.workflow.self_refinement_policy import resolve_self_refinement_policy

    path = repo_root / "configs" / "self_refinement" / "policy.yaml"
    disk_bytes: int | None = None
    if path.is_file():
        try:
            disk_bytes = int(path.stat().st_size)
        except OSError:
            disk_bytes = None
    snap: dict[str, Any]
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        snap = {
            "relpath": "configs/self_refinement/policy.yaml",
            "exists": True,
            "source": "materializer",
        }
        try:
            raw = config_materializer.get_self_refinement_policy()
        except KeyError:
            pol = SelfRefinementPolicy(version=1, enabled=False, description="")
            snap["exists"] = False
            snap["note"] = "missing in materializer — same default as pipeline"
            snap["policy_yaml_file_bytes"] = None
            snap["policy_yaml_top_level_version_int"] = None
            return pol, snap
        pol = resolve_self_refinement_policy(repo_root, config_materializer=config_materializer)
        snap["policy_yaml_file_bytes"] = disk_bytes
        rv = raw.get("version") if isinstance(raw, dict) else None
        snap["policy_yaml_top_level_version_int"] = (
            int(rv) if type(rv) is int and not isinstance(rv, bool) else None
        )
        return pol, snap
    path = repo_root / "configs" / "self_refinement" / "policy.yaml"
    snap = {
        "relpath": "configs/self_refinement/policy.yaml",
        "exists": path.is_file(),
    }
    if not path.is_file():
        pol = SelfRefinementPolicy(version=1, enabled=False, description="")
        snap["note"] = "missing file — same default object as pipeline when policy absent"
        snap["policy_yaml_file_bytes"] = None
        snap["policy_yaml_top_level_version_int"] = None
        return pol, snap
    try:
        snap["policy_yaml_file_bytes"] = int(path.stat().st_size)
    except OSError:
        snap["policy_yaml_file_bytes"] = None
    snap["policy_yaml_top_level_version_int"] = None
    try:
        raw_pol = load_yaml(path)
        if isinstance(raw_pol, dict):
            rv = raw_pol.get("version")
            if type(rv) is int and not isinstance(rv, bool):
                snap["policy_yaml_top_level_version_int"] = rv
    except (OSError, ValueError, UnicodeDecodeError):
        pass
    pol = resolve_self_refinement_policy(repo_root, config_materializer=config_materializer)
    return pol, snap


def _self_refinement_stage_marker_env_disabled() -> bool:
    return env_falsy("NIMBUSWARE_SELF_REFINEMENT_STAGE_MARKER")


def _nimbusware_self_refinement_ungated_loop_env_summary() -> dict[str, Any]:
    return env_tri_state_summary("NIMBUSWARE_SELF_REFINEMENT_UNGATED_LOOP")


def self_refinement_ungated_loop_env_gate_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return env_tri_state_registry_caption(
        payload,
        "NIMBUSWARE_SELF_REFINEMENT_UNGATED_LOOP",
        "self_refinement_ungated_loop",
    )


def _nimbusware_self_refinement_stage_marker_env_summary() -> dict[str, Any]:
    return env_disable_flag_summary(
        "NIMBUSWARE_SELF_REFINEMENT_STAGE_MARKER",
        disable_key="disables_marker",
    )


def _marker_preview(
    wf_sr: SelfRefinementWorkflowBlock,
    pol: SelfRefinementPolicy,
) -> dict[str, Any]:
    version = pol.version
    description = pol.description
    if wf_sr.version is not None:
        version = wf_sr.version
    if wf_sr.description is not None:
        description = wf_sr.description
    max_iterations = pol.max_iterations
    if wf_sr.max_iterations is not None:
        max_iterations = wf_sr.max_iterations
    auto_promote = bool(pol.auto_promote_probation or wf_sr.auto_promote_probation)
    bounded = (description or "")[:2000]
    would_emit = bool(pol.enabled or wf_sr.enabled)
    env_off = _self_refinement_stage_marker_env_disabled()
    ap_raw = env_str("NIMBUSWARE_SELF_REFINEMENT_AUTO_PROMOTE").lower()
    auto_promote_env_off = ap_raw in ("0", "false", "no")
    return {
        "would_emit_self_refinement_marker": would_emit,
        "would_emit_marker_after_env": would_emit and not env_off,
        "merged_version": version,
        "merged_description_preview": bounded,
        "merged_description_len": len(bounded),
        "merged_max_iterations": max_iterations,
        "merged_auto_promote_probation": auto_promote,
        "NIMBUSWARE_SELF_REFINEMENT_STAGE_MARKER": _nimbusware_self_refinement_stage_marker_env_summary(),
        "NIMBUSWARE_SELF_REFINEMENT_AUTO_PROMOTE": env_str(
            "NIMBUSWARE_SELF_REFINEMENT_AUTO_PROMOTE"
        )
        or None,
        "auto_promote_after_env": auto_promote and not auto_promote_env_off,
    }


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
