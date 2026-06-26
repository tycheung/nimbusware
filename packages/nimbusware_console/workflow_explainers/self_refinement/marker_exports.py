from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from functools import partial
from typing import Any

from nimbusware_console.components.operator_metrics import (
    mapping_export_json,
    table_rows_csv,
)


def self_refinement_workflow_explainer_operator_metrics_export_filename_slug() -> str:
    return "self_refinement_workflow_explainer_operator_metrics"


def self_refinement_marker_merge_compare_export_filename_slug() -> str:
    return "self_refinement_marker_compare"


def self_refinement_marker_merge_compare_snapshot(
    marker_merge: Mapping[str, Any] | None,
    timeline_sr: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "marker_merge": marker_merge if isinstance(marker_merge, Mapping) else None,
        "timeline_self_refinement": (timeline_sr if isinstance(timeline_sr, Mapping) else None),
    }


def self_refinement_marker_merge_compare_export_json(
    snapshot: Mapping[str, Any] | None,
) -> str:
    return mapping_export_json(snapshot)


_MARKER_MERGE_COMPARE_CSV_COLUMNS: tuple[str, ...] = (
    "metric",
    "explainer_marker_merge",
    "timeline_self_refinement",
)


def self_refinement_marker_merge_compare_export_json_rows(
    rows: Sequence[Mapping[str, str]],
) -> str:
    out = [dict(r) for r in rows if isinstance(r, Mapping)]
    return json.dumps(out, indent=2, ensure_ascii=False)


self_refinement_marker_merge_compare_table_rows_csv = partial(
    table_rows_csv,
    columns=_MARKER_MERGE_COMPARE_CSV_COLUMNS,
)
