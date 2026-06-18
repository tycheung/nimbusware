from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.mapping import load_error_text
from nimbusware_console.explainer_core.env_captions import env_tri_state_gate_caption


def security_scan_metadata_workflow_yaml_version_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if load_error_text(payload) is not None:
        return None
    raw = payload.get("workflow_yaml_top_level_version_int")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0:
        return None
    return f"Security scan metadata workflow YAML top-level version: **{raw}**."


def security_scan_metadata_workflow_yaml_string_key_count_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if load_error_text(payload) is not None:
        return None
    raw = payload.get("workflow_yaml_top_level_string_key_count")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return f"Security scan metadata workflow YAML top-level string keys: **{raw}**."


def security_scan_metadata_env_gate_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    return env_tri_state_gate_caption(
        payload,
        "NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA",
        label="Security scan metadata",
        forces_off_text=("Security scan metadata env: **{env_key}** kill-switch active{detail}."),
        forces_on_text="Security scan metadata env: **{env_key}** force-on{detail}.",
        unset_text=(
            "Security scan metadata env: **{env_key}** unset — "
            "workflow YAML controls **effective_enabled**."
        ),
        unrecognised_text=(
            "Security scan metadata env: **{env_key}** unrecognised value"
            "{detail} — treated like unset."
        ),
        unset_key="unset_follows_yaml",
    )


def security_scan_metadata_workflow_yaml_relpath_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if load_error_text(payload) is not None:
        return None
    raw = payload.get("workflow_yaml_relpath")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"Security scan metadata workflow YAML: `{text}`."


def security_scan_metadata_workflow_yaml_file_bytes_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if load_error_text(payload) is not None:
        return None
    raw = payload.get("workflow_yaml_file_bytes")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return f"Security scan metadata workflow YAML file: **{raw}** bytes."


def security_scan_metadata_yaml_raw_type_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if load_error_text(payload) is not None:
        return None
    raw_type = payload.get("security_scan_metadata_on_verify_yaml_raw_type")
    if not isinstance(raw_type, str):
        return None
    text = raw_type.strip()
    if not text:
        return None
    return f"Security scan metadata YAML raw type: **{text}**."


def security_scan_metadata_effective_enabled_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if load_error_text(payload) is not None:
        return None
    yaml_parsed = payload.get("yaml_parsed_bool")
    effective = payload.get("effective_enabled")
    if not isinstance(yaml_parsed, bool) or not isinstance(effective, bool):
        return None
    y_label = "true" if yaml_parsed else "false"
    e_label = "true" if effective else "false"
    return (
        f"Security scan metadata: yaml_parsed_bool=**{y_label}**, effective_enabled=**{e_label}**."
    )


def security_scan_metadata_mapping_key_count_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if payload.get("security_scan_metadata_on_verify_yaml_raw_type") != "dict":
        return None
    n = payload.get("security_scan_metadata_on_verify_mapping_string_key_count")
    if not isinstance(n, int) or n < 0:
        return None
    return (
        "Frozen ``security_scan_metadata_on_verify`` block: **"
        f"{n}"
        "** top-level string key(s) in workflow YAML."
    )


def security_scan_metadata_yaml_effective_mismatch_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if payload.get("security_scan_metadata_yaml_parsed_bool_matches_effective") is not False:
        return None
    return (
        "``yaml_parsed_bool`` (workflow file only) differs from **effective_enabled** "
        "(YAML + ``NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA``) — check env kill-switch / force-on."
    )
