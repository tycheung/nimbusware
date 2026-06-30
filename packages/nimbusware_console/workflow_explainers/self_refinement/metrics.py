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
    if metrics.get("would_emit_marker_after_env") is True:
        parts.append("marker **would emit** (after env)")
    elif metrics.get("would_emit_marker") is True:
        parts.append("marker **would emit**")
    if metrics.get("ungated_loop_forces_on") is True:
        parts.append("ungated loop env **forces on**")
    elif metrics.get("ungated_loop_forces_off") is True:
        parts.append("ungated loop env **forces off**")
    if metrics.get("policy_enabled") is True:
        parts.append("policy enabled")
    merged_max = metrics.get("merged_max_iterations")
    if is_strict_int(merged_max):
        parts.append(f"max iterations **{merged_max}**")
    elif metrics.get("yaml_present") is True:
        parts.append("YAML block present")
    if metrics.get("load_error_present") is True:
        parts.append("load error")
    return parts


install_workflow_metrics_from_spec(
    globals(),
    repo_explainer_spec("self_refinement"),
    caption_parts_fn=_caption_parts,
)
