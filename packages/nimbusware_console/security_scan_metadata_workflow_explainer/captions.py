from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def security_scan_metadata_workflow_yaml_version_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
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
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    raw = payload.get("workflow_yaml_top_level_string_key_count")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return (
        "Security scan metadata workflow YAML top-level string keys: "
        f"**{raw}**."
    )


def security_scan_metadata_env_gate_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    env = payload.get("HERMES_ATTACH_SECURITY_SCAN_METADATA")
    if not isinstance(env, Mapping):
        return None
    if env.get("forces_off"):
        raw = env.get("raw")
        detail = f" (raw={raw!r})" if isinstance(raw, str) and raw.strip() else ""
        return (
            "Security scan metadata env: **HERMES_ATTACH_SECURITY_SCAN_METADATA** "
            f"kill-switch active{detail}."
        )
    if env.get("forces_on"):
        raw = env.get("raw")
        detail = f" (raw={raw!r})" if isinstance(raw, str) and raw.strip() else ""
        return (
            "Security scan metadata env: **HERMES_ATTACH_SECURITY_SCAN_METADATA** "
            f"force-on{detail}."
        )
    if env.get("unset_follows_yaml"):
        return (
            "Security scan metadata env: **HERMES_ATTACH_SECURITY_SCAN_METADATA** unset — "
            "workflow YAML controls **effective_enabled**."
        )
    if env.get("unrecognised_value"):
        raw = env.get("raw")
        detail = f" (raw={raw!r})" if isinstance(raw, str) and raw.strip() else ""
        return (
            "Security scan metadata env: **HERMES_ATTACH_SECURITY_SCAN_METADATA** "
            f"unrecognised value{detail} — treated like unset."
        )
    return None


def security_scan_metadata_workflow_yaml_relpath_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
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
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
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
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
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
    load_error = payload.get("load_error")
    if isinstance(load_error, str) and load_error.strip():
        return None
    yaml_parsed = payload.get("yaml_parsed_bool")
    effective = payload.get("effective_enabled")
    if not isinstance(yaml_parsed, bool) or not isinstance(effective, bool):
        return None
    y_label = "true" if yaml_parsed else "false"
    e_label = "true" if effective else "false"
    return (
        "Security scan metadata: yaml_parsed_bool=**"
        f"{y_label}**, effective_enabled=**{e_label}**."
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
        "(YAML + ``HERMES_ATTACH_SECURITY_SCAN_METADATA``) — check env kill-switch / force-on."
    )


