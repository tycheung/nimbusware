from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_config.workflow_read import (
    parse_security_scan_metadata_on_verify_workflow,
    security_scan_metadata_on_verify_enabled,
)
from nimbusware_console.components.workflow_explainer_helpers import relative_under
from nimbusware_console.config_materializer import console_config_materializer
from nimbusware_console.explainer_workflow_disk import load_workflow_profile_documents
from nimbusware_console.security_scan_metadata_workflow_explainer.env import (
    _hermes_attach_security_scan_metadata_env_summary,
)


def security_scan_metadata_workflow_explainer_payload(
    repo_root: Path,
    *,
    workflow_profile: str | None,
) -> dict[str, Any]:
    wf_key = str(workflow_profile).strip() if workflow_profile else ""
    wf_sel: str | None = wf_key if wf_key else None

    mat = console_config_materializer(repo_root)

    workflow_yaml_relpath: str | None = None
    load_error: str | None = None
    yaml_raw: Any | None = None
    yaml_key_present = False
    workflow_yaml_top_level_version_int: int | None = None
    workflow_yaml_top_level_string_key_count: int | None = None
    workflow_yaml_file_bytes: int | None = None

    if wf_sel:
        try:
            disk_doc, _effective_doc, wp, file_bytes = load_workflow_profile_documents(
                repo_root,
                wf_sel,
                materializer=mat,
            )
            workflow_yaml_relpath = relative_under(repo_root, wp)
            workflow_yaml_file_bytes = file_bytes
            doc = disk_doc
            if isinstance(doc, dict):
                workflow_yaml_top_level_string_key_count = sum(1 for k in doc if isinstance(k, str))
                vtop = doc.get("version")
                if type(vtop) is int and not isinstance(vtop, bool):
                    workflow_yaml_top_level_version_int = vtop
                if "security_scan_metadata_on_verify" in doc:
                    yaml_key_present = True
                    yaml_raw = doc.get("security_scan_metadata_on_verify")
        except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError) as err:
            load_error = str(err)
            yaml_raw = None

    yaml_parsed = parse_security_scan_metadata_on_verify_workflow(
        repo_root,
        wf_sel,
        config_materializer=mat,
    )
    effective = security_scan_metadata_on_verify_enabled(
        repo_root,
        wf_sel,
        config_materializer=mat,
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
        "HERMES_ATTACH_SECURITY_SCAN_METADATA": _hermes_attach_security_scan_metadata_env_summary(),
        "load_error": load_error,
    }
