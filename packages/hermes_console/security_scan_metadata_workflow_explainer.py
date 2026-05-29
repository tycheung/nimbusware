"""Read-only ``security_scan_metadata_on_verify`` + env for Streamlit (§14 #18 / fo136)."""

from __future__ import annotations

import csv
import json
import os
from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import Any

import hermes_orchestrator.pipeline  # noqa: F401 — break extensions↔orchestrator cycle
from hermes_console.config_materializer import console_config_materializer
from hermes_console.explainer_workflow_disk import load_workflow_profile_documents
from hermes_orchestrator.workflow_security import security_scan_metadata_on_verify_enabled
from hermes_orchestrator.workflow_security_metadata import (
    parse_security_scan_metadata_on_verify_workflow,
)


def _relative_under(repo_root: Path, path: Path) -> str:
    root = repo_root.resolve()
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path.resolve())


def _hermes_attach_security_scan_metadata_env_summary() -> dict[str, Any]:
    """Mirror ``workflow_security.security_scan_metadata_on_verify_enabled`` env branch."""
    raw = os.environ.get("HERMES_ATTACH_SECURITY_SCAN_METADATA", "")
    low = raw.strip().lower()
    if not low:
        return {
            "raw": raw,
            "forces_off": False,
            "forces_on": False,
            "unset_follows_yaml": True,
        }
    if low in ("0", "false", "no"):
        return {
            "raw": raw,
            "forces_off": True,
            "forces_on": False,
            "unset_follows_yaml": False,
        }
    if low in ("1", "true", "yes"):
        return {
            "raw": raw,
            "forces_off": False,
            "forces_on": True,
            "unset_follows_yaml": False,
        }
    return {
        "raw": raw,
        "forces_off": False,
        "forces_on": False,
        "unset_follows_yaml": True,
        "unrecognised_value": True,
    }


def security_scan_metadata_workflow_explainer_payload(
    repo_root: Path,
    *,
    workflow_profile: str | None,
) -> dict[str, Any]:
    """Frozen workflow YAML value vs ``HERMES_ATTACH_SECURITY_SCAN_METADATA`` vs effective flag."""
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
            workflow_yaml_relpath = _relative_under(repo_root, wp)
            workflow_yaml_file_bytes = file_bytes
            doc = disk_doc
            if isinstance(doc, dict):
                workflow_yaml_top_level_string_key_count = sum(
                    1 for k in doc if isinstance(k, str)
                )
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
        "security_scan_metadata_on_verify_mapping_string_key_count": (
            ssm_mapping_string_key_count
        ),
        "yaml_parsed_bool": yaml_parsed,
        "effective_enabled": effective,
        "security_scan_metadata_yaml_parsed_bool_matches_effective": (
            yaml_parsed_bool_matches_effective
        ),
        "HERMES_ATTACH_SECURITY_SCAN_METADATA": _hermes_attach_security_scan_metadata_env_summary(),
        "load_error": load_error,
    }


def security_scan_metadata_workflow_yaml_version_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    """Top-level ``version`` int from the selected workflow profile YAML on disk."""
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
    """Count of top-level string keys in the selected workflow profile YAML."""
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
    """One-line summary of ``HERMES_ATTACH_SECURITY_SCAN_METADATA`` env gate."""
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
    """Repo-relative workflow profile path from the explainer payload."""
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
    """On-disk workflow YAML file size from the explainer payload."""
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
    """Python type name of frozen ``security_scan_metadata_on_verify`` YAML value."""
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
    """One-line ``yaml_parsed_bool`` vs pipeline ``effective_enabled``."""
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
    """Surface how many string keys sit under a mapping ``security_scan_metadata_on_verify``."""
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
    """Surface when ``yaml_parsed_bool`` disagrees with ``effective_enabled`` (env override)."""
    if not isinstance(payload, Mapping):
        return None
    if payload.get("security_scan_metadata_yaml_parsed_bool_matches_effective") is not False:
        return None
    return (
        "``yaml_parsed_bool`` (workflow file only) differs from **effective_enabled** "
        "(YAML + ``HERMES_ATTACH_SECURITY_SCAN_METADATA``) — check env kill-switch / force-on."
    )


def security_scan_metadata_export_filename_slug() -> str:
    """Filename slug prefix for security scan metadata explainer exports."""
    return "security_scan_metadata"


_SECURITY_SCAN_METADATA_EXPLAINER_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def _security_scan_metadata_explainer_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def security_scan_metadata_explainer_table_rows(
    payload: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Sorted field/value rows for security scan metadata explainer export."""
    if not isinstance(payload, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for key in sorted(str(k) for k in payload.keys()):
        rows.append(
            {
                "field": key,
                "value": _security_scan_metadata_explainer_cell(payload.get(key)),
            },
        )
    return rows


def security_scan_metadata_explainer_export_json(
    payload: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for security scan metadata explainer payload."""
    if not isinstance(payload, Mapping):
        return "{}"
    return json.dumps(dict(payload), indent=2, ensure_ascii=False)


def security_scan_metadata_explainer_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize security scan metadata explainer field/value rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_SECURITY_SCAN_METADATA_EXPLAINER_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _SECURITY_SCAN_METADATA_EXPLAINER_CSV_COLUMNS
                },
            )
    return buf.getvalue()


_SECURITY_SCAN_METADATA_WORKFLOW_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)


def security_scan_metadata_workflow_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Rollup over :func:`security_scan_metadata_workflow_explainer_payload` (§14 #18)."""
    metrics: dict[str, Any] = {
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
    if not isinstance(payload, Mapping):
        return metrics
    metrics["yaml_key_present"] = (
        payload.get("security_scan_metadata_on_verify_yaml_key_present") is True
    )
    metrics["yaml_parsed_bool"] = payload.get("yaml_parsed_bool") is True
    metrics["effective_enabled"] = payload.get("effective_enabled") is True
    matches = payload.get("security_scan_metadata_yaml_parsed_bool_matches_effective")
    metrics["yaml_matches_effective"] = matches is True
    if matches is False:
        metrics["yaml_effective_mismatch"] = True
    env = payload.get("HERMES_ATTACH_SECURITY_SCAN_METADATA")
    if isinstance(env, dict):
        metrics["env_forces_on"] = env.get("forces_on") is True
        metrics["env_forces_off"] = env.get("forces_off") is True
        metrics["env_unset"] = env.get("unset") is True
    err = payload.get("load_error")
    metrics["load_error_present"] = isinstance(err, str) and bool(err.strip())
    ver = payload.get("workflow_yaml_top_level_version_int")
    if isinstance(ver, int) and not isinstance(ver, bool):
        metrics["workflow_yaml_version_int"] = ver
    raw_bytes = payload.get("workflow_yaml_file_bytes")
    if isinstance(raw_bytes, int) and not isinstance(raw_bytes, bool) and raw_bytes >= 0:
        metrics["workflow_yaml_file_bytes"] = raw_bytes
    return metrics


def security_scan_metadata_workflow_explainer_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {
            "field": "YAML key present",
            "value": str(metrics.get("yaml_key_present", False)).lower(),
        },
        {
            "field": "YAML parsed bool",
            "value": str(metrics.get("yaml_parsed_bool", False)).lower(),
        },
        {
            "field": "Effective enabled",
            "value": str(metrics.get("effective_enabled", False)).lower(),
        },
        {
            "field": "YAML matches effective",
            "value": str(metrics.get("yaml_matches_effective", True)).lower(),
        },
        {
            "field": "YAML/effective mismatch",
            "value": str(metrics.get("yaml_effective_mismatch", False)).lower(),
        },
        {"field": "Env forces on", "value": str(metrics.get("env_forces_on", False)).lower()},
        {"field": "Env forces off", "value": str(metrics.get("env_forces_off", False)).lower()},
        {"field": "Env unset", "value": str(metrics.get("env_unset", True)).lower()},
    ]
    ver = metrics.get("workflow_yaml_version_int")
    if isinstance(ver, int) and not isinstance(ver, bool):
        rows.append({"field": "Workflow YAML version", "value": str(ver)})
    raw_bytes = metrics.get("workflow_yaml_file_bytes")
    if isinstance(raw_bytes, int) and not isinstance(raw_bytes, bool):
        rows.append({"field": "Workflow YAML bytes", "value": str(raw_bytes)})
    if metrics.get("load_error_present") is True:
        rows.append({"field": "Load error", "value": "yes"})
    return rows


def security_scan_metadata_workflow_explainer_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON export of workflow explainer operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def security_scan_metadata_workflow_explainer_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize security scan metadata workflow explainer operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(
            _SECURITY_SCAN_METADATA_WORKFLOW_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS,
        ),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _SECURITY_SCAN_METADATA_WORKFLOW_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def security_scan_metadata_workflow_explainer_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption for security scan metadata explainer metrics."""
    if not isinstance(metrics, Mapping):
        return None
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
    if isinstance(raw_bytes, int) and not isinstance(raw_bytes, bool) and raw_bytes > 0:
        parts.append(f"workflow YAML **{raw_bytes}** byte(s)")
    if metrics.get("load_error_present") is True:
        parts.append("load error")
    if not parts:
        return None
    return "Security scan metadata explainer metrics: " + ", ".join(parts) + "."


def security_scan_metadata_workflow_explainer_operator_metrics_export_filename_slug() -> str:
    """Stable slug for security scan metadata workflow explainer operator metrics downloads."""
    return "security_scan_metadata_workflow_explainer_operator_metrics"
