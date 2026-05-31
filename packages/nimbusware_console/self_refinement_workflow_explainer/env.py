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

def _load_policy_or_default(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> tuple[SelfRefinementPolicy, dict[str, Any]]:
    path = repo_root / "configs" / "self_refinement" / "policy.yaml"
    disk_bytes: int | None = None
    if path.is_file():
        try:
            disk_bytes = int(path.stat().st_size)
        except OSError:
            disk_bytes = None
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        snap: dict[str, Any] = {
            "relpath": "configs/self_refinement/policy.yaml",
            "exists": True,
            "source": "materializer",
        }
        try:
            raw = config_materializer.get_self_refinement_policy()
            pol = self_refinement_policy_from_mapping(raw)
            snap["policy_yaml_file_bytes"] = disk_bytes
            rv = raw.get("version") if isinstance(raw, dict) else None
            snap["policy_yaml_top_level_version_int"] = (
                int(rv) if type(rv) is int and not isinstance(rv, bool) else None
            )
            if snap["policy_yaml_top_level_version_int"] is None and path.is_file():
                try:
                    raw_pol = load_yaml(path)
                    if isinstance(raw_pol, dict):
                        rv_disk = raw_pol.get("version")
                        if type(rv_disk) is int and not isinstance(rv_disk, bool):
                            snap["policy_yaml_top_level_version_int"] = rv_disk
                except (OSError, ValueError, UnicodeDecodeError):
                    pass
            return pol, snap
        except KeyError:
            pol = SelfRefinementPolicy(version=1, enabled=False, description="")
            snap["exists"] = False
            snap["note"] = "missing in materializer — same default as pipeline"
            snap["policy_yaml_file_bytes"] = None
            snap["policy_yaml_top_level_version_int"] = None
            return pol, snap
    path = repo_root / "configs" / "self_refinement" / "policy.yaml"
    snap: dict[str, Any] = {
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
    pol = load_self_refinement_policy(path)
    return pol, snap


def _self_refinement_stage_marker_env_disabled() -> bool:
    raw = os.environ.get("HERMES_SELF_REFINEMENT_STAGE_MARKER", "").strip().lower()
    return raw in ("0", "false", "no")


def _hermes_self_refinement_ungated_loop_env_summary() -> dict[str, Any]:
    raw = os.environ.get("HERMES_SELF_REFINEMENT_UNGATED_LOOP", "")
    low = raw.strip().lower()
    if not low:
        return {
            "raw": raw,
            "forces_on": False,
            "forces_off": False,
            "unset": True,
        }
    if low in ("1", "true", "yes"):
        return {
            "raw": raw,
            "forces_on": True,
            "forces_off": False,
            "unset": False,
        }
    if low in ("0", "false", "no"):
        return {
            "raw": raw,
            "forces_on": False,
            "forces_off": True,
            "unset": False,
        }
    return {
        "raw": raw,
        "forces_on": False,
        "forces_off": False,
        "unset": True,
        "unrecognised_value": True,
    }


def self_refinement_ungated_loop_env_gate_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    env = payload.get("HERMES_SELF_REFINEMENT_UNGATED_LOOP")
    if not isinstance(env, Mapping):
        return None
    if env.get("forces_on"):
        raw = env.get("raw")
        detail = f" (raw={raw!r})" if isinstance(raw, str) and raw.strip() else ""
        return (
            "Self-refinement ungated env: **HERMES_SELF_REFINEMENT_UNGATED_LOOP** force-on"
            f"{detail} — overrides workflow ``ungated_loop`` when set."
        )
    if env.get("forces_off"):
        raw = env.get("raw")
        detail = f" (raw={raw!r})" if isinstance(raw, str) and raw.strip() else ""
        return (
            "Self-refinement ungated env: **HERMES_SELF_REFINEMENT_UNGATED_LOOP** force-off"
            f"{detail}."
        )
    if env.get("unset"):
        return (
            "Self-refinement ungated env: **HERMES_SELF_REFINEMENT_UNGATED_LOOP** unset — "
            "workflow ``self_refinement.ungated_loop`` controls ungated progression."
        )
    if env.get("unrecognised_value"):
        raw = env.get("raw")
        detail = f" (raw={raw!r})" if isinstance(raw, str) and raw.strip() else ""
        return (
            "Self-refinement ungated env: **HERMES_SELF_REFINEMENT_UNGATED_LOOP** "
            f"unrecognised value{detail} — treated like unset."
        )
    return None


def _hermes_self_refinement_stage_marker_env_summary() -> dict[str, Any]:
    raw = os.environ.get("HERMES_SELF_REFINEMENT_STAGE_MARKER", "")
    low = raw.strip().lower()
    if not low:
        return {
            "raw": raw,
            "disables_marker": False,
            "unset": True,
        }
    if low in ("0", "false", "no"):
        return {
            "raw": raw,
            "disables_marker": True,
            "unset": False,
        }
    return {
        "raw": raw,
        "disables_marker": False,
        "unset": False,
        "unrecognised_value": True,
    }


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
    ap_raw = os.environ.get("HERMES_SELF_REFINEMENT_AUTO_PROMOTE", "").strip().lower()
    auto_promote_env_off = ap_raw in ("0", "false", "no")
    return {
        "would_emit_self_refinement_marker": would_emit,
        "would_emit_marker_after_env": would_emit and not env_off,
        "merged_version": version,
        "merged_description_preview": bounded,
        "merged_description_len": len(bounded),
        "merged_max_iterations": max_iterations,
        "merged_auto_promote_probation": auto_promote,
        "HERMES_SELF_REFINEMENT_STAGE_MARKER": _hermes_self_refinement_stage_marker_env_summary(),
        "HERMES_SELF_REFINEMENT_AUTO_PROMOTE": os.environ.get(
            "HERMES_SELF_REFINEMENT_AUTO_PROMOTE",
            "",
        ).strip()
        or None,
        "auto_promote_after_env": auto_promote and not auto_promote_env_off,
    }


