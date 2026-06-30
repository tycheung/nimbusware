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
    if metrics.get("suppress_automatic_escalation_effective") is True:
        parts.append("suppress automatic **on**")
    else:
        parts.append("suppress automatic **off**")
    if metrics.get("policy_yaml_exists") is True:
        parts.append("policy file present")
    else:
        parts.append("policy file missing")
    if metrics.get("anti_deadlock_mapping_present") is True:
        mp = metrics.get("anti_deadlock_min_progress_events")
        if is_strict_int(mp):
            parts.append(f"anti_deadlock min_progress **{mp}**")
        elif metrics.get("anti_deadlock_enabled") is True:
            parts.append("anti_deadlock **enabled**")
    age = metrics.get("policy_yaml_age_seconds")
    if is_strict_int(age):
        parts.append(f"policy age **{age}s**")
    raw_bytes = metrics.get("policy_yaml_file_bytes")
    if is_strict_int(raw_bytes) and raw_bytes > 0:
        parts.append(f"policy YAML **{raw_bytes}** byte(s)")
    if metrics.get("load_error_present") is True:
        parts.append("load error")
    return parts


install_workflow_metrics_from_spec(
    globals(),
    repo_explainer_spec("escalation_suppress"),
    caption_parts_fn=_caption_parts,
)
