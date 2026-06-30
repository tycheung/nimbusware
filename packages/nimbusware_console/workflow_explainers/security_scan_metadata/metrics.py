from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.coercion import is_strict_int
from nimbusware_console.explainer_core.workflow_metrics_spec import (
    install_workflow_metrics_from_spec,
    repo_explainer_spec,
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


install_workflow_metrics_from_spec(
    globals(),
    repo_explainer_spec("security_scan_metadata"),
    caption_parts_fn=_caption_parts,
)
