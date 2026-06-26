from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.explainer_core.compare_timeline import (
    NO_TIMELINE,
    timeline_present_caption,
    version_alignment_note,
    version_as_optional_int,
)

_version_as_optional_int = version_as_optional_int


def _timeline_self_refinement_description_len(sr: Mapping[str, Any]) -> int:
    desc = sr.get("description")
    if isinstance(desc, str):
        return len(desc)
    if desc is None:
        return 0
    return len(str(desc))


def self_refinement_marker_merge_vs_timeline_rows(
    marker_merge: Mapping[str, Any] | None,
    timeline_sr: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    mm: Mapping[str, Any] = marker_merge if isinstance(marker_merge, Mapping) else {}
    tl: Mapping[str, Any] | None = timeline_sr if isinstance(timeline_sr, Mapping) else None

    pre = mm.get("would_emit_self_refinement_marker")
    post = mm.get("would_emit_marker_after_env")
    tl_pre = timeline_present_caption(tl)
    tl_post = tl_pre

    expl_ver = mm.get("merged_version")
    tl_ver = tl.get("version") if tl is not None else None
    tl_ver_disp = NO_TIMELINE if tl is None else ("—" if tl_ver is None else str(tl_ver))
    align = version_alignment_note(
        explainer_version=expl_ver,
        timeline_version=tl_ver,
        timeline_absent=tl is None,
    )

    expl_dlen = int(mm.get("merged_description_len") or 0)
    tl_dlen = _timeline_self_refinement_description_len(tl) if tl is not None else 0
    delta = NO_TIMELINE if tl is None else str(expl_dlen - tl_dlen)

    tl_mc = tl.get("marker_count") if tl is not None else None
    if tl is None:
        tl_mc_disp = NO_TIMELINE
    elif isinstance(tl_mc, int) and tl_mc >= 0:
        tl_mc_disp = str(tl_mc)
    else:
        tl_mc_disp = "—"

    return [
        {
            "metric": "Would emit marker (workflow ∪ policy)",
            "explainer_marker_merge": str(pre),
            "timeline_self_refinement": tl_pre,
        },
        {
            "metric": "Would emit after env (effective)",
            "explainer_marker_merge": str(post),
            "timeline_self_refinement": tl_post,
        },
        {
            "metric": "Session marker_count (timeline read-model)",
            "explainer_marker_merge": NO_TIMELINE,
            "timeline_self_refinement": tl_mc_disp,
        },
        {
            "metric": "Version (raw)",
            "explainer_marker_merge": str(expl_ver),
            "timeline_self_refinement": tl_ver_disp,
        },
        {
            "metric": "Version (int) alignment",
            "explainer_marker_merge": align,
            "timeline_self_refinement": NO_TIMELINE,
        },
        {
            "metric": "Description length (chars)",
            "explainer_marker_merge": str(expl_dlen),
            "timeline_self_refinement": NO_TIMELINE if tl is None else str(tl_dlen),
        },
        {
            "metric": "Description length delta (explainer − timeline)",
            "explainer_marker_merge": delta,
            "timeline_self_refinement": NO_TIMELINE,
        },
    ]
