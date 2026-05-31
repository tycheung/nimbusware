from __future__ import annotations

from nimbusware_console.components.operator_metrics import (
    FIELD_VALUE_COLUMNS,
    field_value_table_rows_csv,
    mapping_export_json,
    mapping_to_sorted_table_rows,
    sequence_export_json,
    table_rows_csv,
)
import csv
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from io import StringIO
from pathlib import Path
from typing import Any

from nimbusware_console.config_materializer import console_config_materializer
from nimbusware_console.explainer_workflow_disk import load_workflow_profile_documents
from hermes_extensions.self_refinement import (
    SelfRefinementPolicy,
    load_self_refinement_policy,
    self_refinement_policy_from_mapping,
)
from nimbusware_config.workflow_read import (
    SelfRefinementWorkflowBlock,
    load_yaml,
    parse_self_refinement_workflow_block,
    workflow_profile_dict,
    workflow_profile_path,
)
from nimbusware_console.components.workflow_explainer_helpers import relative_under

def _timeline_self_refinement_description_len(sr: Mapping[str, Any]) -> int:
    desc = sr.get("description")
    if isinstance(desc, str):
        return len(desc)
    if desc is None:
        return 0
    return len(str(desc))


def _version_as_optional_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def self_refinement_marker_merge_vs_timeline_rows(
    marker_merge: Mapping[str, Any] | None,
    timeline_sr: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    mm: Mapping[str, Any] = marker_merge if isinstance(marker_merge, Mapping) else {}
    no_tl = "—"
    tl: Mapping[str, Any] | None = timeline_sr if isinstance(timeline_sr, Mapping) else None

    pre = mm.get("would_emit_self_refinement_marker")
    post = mm.get("would_emit_marker_after_env")
    if tl is None:
        tl_pre = no_tl
    elif tl:
        tl_pre = "snapshot present"
    else:
        tl_pre = "(empty object)"
    tl_post = tl_pre

    expl_ver = mm.get("merged_version")
    tl_ver = tl.get("version") if tl is not None else None
    tl_ver_disp = no_tl if tl is None else ("—" if tl_ver is None else str(tl_ver))
    expl_i = _version_as_optional_int(expl_ver)
    tl_i = _version_as_optional_int(tl_ver) if tl is not None else None
    if tl is None:
        align = no_tl
    elif expl_i is None or tl_i is None:
        align = "n/a (need integer-like versions on both sides)"
    elif expl_i == tl_i:
        align = "match"
    else:
        align = f"mismatch (explainer {expl_i} vs timeline {tl_i})"

    expl_dlen = int(mm.get("merged_description_len") or 0)
    tl_dlen = _timeline_self_refinement_description_len(tl) if tl is not None else 0
    delta = no_tl if tl is None else str(expl_dlen - tl_dlen)

    tl_mc = tl.get("marker_count") if tl is not None else None
    if tl is None:
        tl_mc_disp = no_tl
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
            "explainer_marker_merge": no_tl,
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
            "timeline_self_refinement": no_tl,
        },
        {
            "metric": "Description length (chars)",
            "explainer_marker_merge": str(expl_dlen),
            "timeline_self_refinement": no_tl if tl is None else str(tl_dlen),
        },
        {
            "metric": "Description length delta (explainer − timeline)",
            "explainer_marker_merge": delta,
            "timeline_self_refinement": no_tl,
        },
    ]


