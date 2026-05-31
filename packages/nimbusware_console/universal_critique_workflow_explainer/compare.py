from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def universal_critique_workflow_vs_timeline_rows(
    explainer_payload: Mapping[str, Any] | None,
    timeline_uc: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    exp: Mapping[str, Any] = (
        explainer_payload if isinstance(explainer_payload, Mapping) else {}
    )
    no_tl = "—"
    tl: Mapping[str, Any] | None = (
        timeline_uc if isinstance(timeline_uc, Mapping) else None
    )

    wf_enabled = exp.get("universal_critique_yaml_top_level_enabled_true_count")
    wf_enabled_disp = (
        no_tl
        if not isinstance(wf_enabled, int) or isinstance(wf_enabled, bool)
        else str(wf_enabled)
    )

    if tl is None:
        tl_stage_disp = no_tl
        tl_fail_disp = no_tl
    else:
        sc = tl.get("stage_count")
        tl_stage_disp = (
            no_tl if not isinstance(sc, int) or isinstance(sc, bool) else str(sc)
        )
        fc = tl.get("fail_count")
        tl_fail_disp = (
            no_tl if not isinstance(fc, int) or isinstance(fc, bool) else str(fc)
        )

    align = no_tl
    if tl is not None and isinstance(wf_enabled, int) and not isinstance(wf_enabled, bool):
        sc_i = tl.get("stage_count")
        if isinstance(sc_i, int) and not isinstance(sc_i, bool):
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
            "workflow_explainer": no_tl,
            "timeline_universal_critique": tl_fail_disp,
        },
        {
            "metric": "Alignment note",
            "workflow_explainer": no_tl,
            "timeline_universal_critique": align,
        },
    ]


def universal_critique_env_override_deltas(payload: Mapping[str, Any]) -> list[dict[str, str]]:
    yo = payload.get("yaml_only")
    eff = payload.get("effective_with_env")
    if not isinstance(yo, dict) or not isinstance(eff, dict):
        return []
    rows: list[dict[str, str]] = []
    for k in sorted(yo.keys()):
        if k not in eff:
            continue
        yv, ev = yo[k], eff[k]
        if yv != ev:
            rows.append(
                {"knob": k, "yaml_only": str(yv), "effective_with_env": str(ev)},
            )
    return rows


