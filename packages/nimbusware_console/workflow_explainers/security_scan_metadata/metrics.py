from __future__ import annotations

from agent_core.coercion import is_strict_int
from collections.abc import Mapping
from typing import Any

from nimbusware_console.explainer_core.operator_metrics_exports import (
    build_metrics_fn,
    caption_from_parts,
    install_operator_metrics_module,
    table_rows_fn,
)

_PREFIX = "security_scan_metadata_workflow_explainer"

_DEFAULTS: dict[str, Any] = {
    "yaml_key_present": False,
    "yaml_parsed_bool": False,
    "effective_enabled": False,
    "yaml_matches_effective": True,
    "yaml_effective_mismatch": False,
    "env_forces_on": False,
    "env_forces_off": False,
    "env_unset": True,
    "load_error_present": False,
    "workflow_yaml_version_int": None,
    "workflow_yaml_file_bytes": None,
}

_TABLE_ROWS: tuple[tuple[str, str], ...] = (
    ("YAML key present", "yaml_key_present"),
    ("YAML parsed bool", "yaml_parsed_bool"),
    ("Effective enabled", "effective_enabled"),
    ("YAML matches effective", "yaml_matches_effective"),
    ("YAML/effective mismatch", "yaml_effective_mismatch"),
    ("Env forces on", "env_forces_on"),
    ("Env forces off", "env_forces_off"),
    ("Env unset", "env_unset"),
    ("Workflow YAML version", "workflow_yaml_version_int"),
    ("Workflow YAML bytes", "workflow_yaml_file_bytes"),
    ("Load error", "load_error_present"),
)


def _caption_parts(metrics: Mapping[str, Any]) -> list[str]:
    parts: list[str] = []
    if metrics.get("yaml_matches_effective") is False:
        parts.append("YAML vs effective **mismatch**")
    if metrics.get("env_forces_on") is True:
        parts.append("env **forces on**")
    elif metrics.get("env_forces_off") is True:
        parts.append("env **forces off**")
    if metrics.get("effective_enabled") is True:
        parts.append("effective **enabled**")
    elif metrics.get("yaml_parsed_bool") is False and metrics.get("yaml_key_present") is True:
        parts.append("effective **disabled**")
    raw_bytes = metrics.get("workflow_yaml_file_bytes")
    if is_strict_int(raw_bytes) and raw_bytes > 0:
        parts.append(f"workflow YAML **{raw_bytes}** byte(s)")
    if metrics.get("load_error_present") is True:
        parts.append("load error")
    return parts


(
    security_scan_metadata_workflow_explainer_operator_metrics,
    security_scan_metadata_workflow_explainer_operator_metrics_table_rows,
    security_scan_metadata_workflow_explainer_operator_metrics_caption,
    security_scan_metadata_workflow_explainer_operator_metrics_export_json,
    security_scan_metadata_workflow_explainer_operator_metrics_table_rows_csv,
    security_scan_metadata_workflow_explainer_operator_metrics_export_filename_slug,
) = install_operator_metrics_module(
    globals(),
    module_prefix=_PREFIX,
    metrics=build_metrics_fn(
        _DEFAULTS,
        bool_fields=(
            ("security_scan_metadata_on_verify_yaml_key_present", "yaml_key_present"),
            ("yaml_parsed_bool", "yaml_parsed_bool"),
            ("effective_enabled", "effective_enabled"),
        ),
        bool_match_fields=(
            (
                "security_scan_metadata_yaml_parsed_bool_matches_effective",
                "yaml_matches_effective",
                "yaml_effective_mismatch",
            ),
        ),
        env_tri_state=("NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA",),
        workflow_yaml_file=True,
        load_error=True,
    ),
    table_rows=table_rows_fn(
        _TABLE_ROWS,
        append_load_error_row=True,
        exclude_keys=frozenset({"load_error_present"}),
    ),
    caption=caption_from_parts("Security scan metadata explainer metrics: ", _caption_parts),
)
