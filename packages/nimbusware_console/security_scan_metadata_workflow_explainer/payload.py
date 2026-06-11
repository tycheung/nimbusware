from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_config.workflow_read import (
    parse_security_scan_metadata_on_verify_workflow,
    security_scan_metadata_on_verify_enabled,
)
from nimbusware_console.explainer_core.workflow_profile import load_workflow_disk_snapshot
from nimbusware_console.security_scan_metadata_workflow_explainer.env import (
    _nimbusware_attach_security_scan_metadata_env_summary,
)


def security_scan_metadata_workflow_explainer_payload(
    repo_root: Path,
    *,
    workflow_profile: str | None,
) -> dict[str, Any]:
    snap = load_workflow_disk_snapshot(repo_root, workflow_profile)
    wf_sel = snap.workflow_profile
    workflow_yaml_relpath = snap.workflow_yaml_relpath
    load_error = snap.load_error
    workflow_yaml_top_level_version_int = snap.version_int
    workflow_yaml_file_bytes = snap.file_bytes
    workflow_yaml_top_level_string_key_count = (
        sum(1 for k in snap.disk_doc if isinstance(k, str)) if snap.disk_doc else None
    )
    yaml_key_present = "security_scan_metadata_on_verify" in snap.disk_doc
    yaml_raw = snap.disk_doc.get("security_scan_metadata_on_verify") if yaml_key_present else None

    yaml_parsed = parse_security_scan_metadata_on_verify_workflow(
        repo_root,
        wf_sel,
        config_materializer=snap.materializer,
    )
    effective = security_scan_metadata_on_verify_enabled(
        repo_root,
        wf_sel,
        config_materializer=snap.materializer,
    )

    yaml_parsed_bool_matches_effective = bool(yaml_parsed) == bool(effective)

    yaml_raw_type: str | None
    if yaml_raw is None:
        yaml_raw_type = None
    else:
        yaml_raw_type = type(yaml_raw).__name__

    ssm_mapping_string_key_count: int | None = None
    if isinstance(yaml_raw, dict):
        ssm_mapping_string_key_count = sum(1 for k in yaml_raw if isinstance(k, str))

    return {
        "workflow_profile": wf_sel,
        "workflow_yaml_relpath": workflow_yaml_relpath,
        "workflow_yaml_top_level_version_int": workflow_yaml_top_level_version_int,
        "workflow_yaml_top_level_string_key_count": workflow_yaml_top_level_string_key_count,
        "workflow_yaml_file_bytes": workflow_yaml_file_bytes,
        "security_scan_metadata_on_verify_yaml_key_present": yaml_key_present,
        "security_scan_metadata_on_verify_yaml_value": yaml_raw,
        "security_scan_metadata_on_verify_yaml_raw_type": yaml_raw_type,
        "security_scan_metadata_on_verify_mapping_string_key_count": (ssm_mapping_string_key_count),
        "yaml_parsed_bool": yaml_parsed,
        "effective_enabled": effective,
        "security_scan_metadata_yaml_parsed_bool_matches_effective": (
            yaml_parsed_bool_matches_effective
        ),
        "NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA": _nimbusware_attach_security_scan_metadata_env_summary(),
        "load_error": load_error,
    }
