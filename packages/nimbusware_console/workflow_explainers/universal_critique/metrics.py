from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.coercion import is_strict_int
from nimbusware_console.explainer_core.workflow_metrics_spec import (
    install_workflow_metrics_from_spec,
    repo_explainer_spec,
)


def _caption_parts(metrics: Mapping[str, Any]) -> list[str]:
    if metrics.get("yaml_present") is not True:
        return []
    nkeys = metrics.get("top_level_key_count", 0)
    if not isinstance(nkeys, int) or isinstance(nkeys, bool):
        nkeys = 0
    enabled = metrics.get("enabled_true_count", 0)
    if not isinstance(enabled, int) or isinstance(enabled, bool):
        enabled = 0
    parts = [
        f"**{nkeys}** stage key(s)",
        f"**{enabled}** with ``enabled: true``",
    ]
    if metrics.get("default_enabled_on") is True:
        parts.append("``default_enabled`` **on**")
    if metrics.get("unanimous_gate_enforce") is True:
        parts.append("unanimous gate **on**")
    if metrics.get("fw_enabled") is True:
        parts.append("fw panel **on**")
    if metrics.get("mi_enabled") is True:
        parts.append("mi panel **on**")
    lists = metrics.get("list_child_count", 0)
    if is_strict_int(lists) and lists > 0:
        parts.append(f"**{lists}** list child(ren)")
    scalar = metrics.get("scalar_leaf_count", 0)
    if is_strict_int(scalar) and scalar > 0:
        parts.append(f"**{scalar}** scalar leaf(es)")
    return parts


install_workflow_metrics_from_spec(
    globals(),
    repo_explainer_spec("universal_critique"),
    caption_parts_fn=_caption_parts,
)
