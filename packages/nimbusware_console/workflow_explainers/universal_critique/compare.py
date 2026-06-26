from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.coercion import is_strict_int
from nimbusware_console.explainer_core.compare_timeline import (
    NO_TIMELINE,
    env_override_delta_rows,
    timeline_int_field,
)


def universal_critique_workflow_vs_timeline_rows(
    explainer_payload: Mapping[str, Any] | None,
    timeline_uc: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    exp: Mapping[str, Any] = explainer_payload if isinstance(explainer_payload, Mapping) else {}
    tl: Mapping[str, Any] | None = timeline_uc if isinstance(timeline_uc, Mapping) else None

    wf_enabled = exp.get("universal_critique_yaml_top_level_enabled_true_count")
    wf_enabled_disp = (
        NO_TIMELINE
        if not isinstance(wf_enabled, int) or isinstance(wf_enabled, bool)
        else str(wf_enabled)
    )

    tl_stage_disp = timeline_int_field(tl, "stage_count")
    tl_fail_disp = timeline_int_field(tl, "fail_count")

    align = NO_TIMELINE
    if tl is not None and is_strict_int(wf_enabled):
        sc_i = tl.get("stage_count")
        if is_strict_int(sc_i):
            if wf_enabled == sc_i:
                align = "stage_count matches enabled:true count"
            else:
                align = f"mismatch (workflow enabled:true={wf_enabled} vs timeline stages={sc_i})"

    return [
        {
            "metric": "YAML stages with enabled: true",
            "workflow_explainer": wf_enabled_disp,
            "timeline_universal_critique": tl_stage_disp,
        },
        {
            "metric": "FAIL gate count (timeline)",
            "workflow_explainer": NO_TIMELINE,
            "timeline_universal_critique": tl_fail_disp,
        },
        {
            "metric": "Alignment note",
            "workflow_explainer": NO_TIMELINE,
            "timeline_universal_critique": align,
        },
    ]


def universal_critique_env_override_deltas(payload: Mapping[str, Any]) -> list[dict[str, str]]:
    return env_override_delta_rows(payload)
