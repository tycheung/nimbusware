from __future__ import annotations

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
    mapping_to_sorted_table_rows,
    table_rows_csv,
)
import csv
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import Any

def persona_catalog_operator_summary(catalog: Mapping[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "catalog_version": catalog.get("version"),
        "business_area_count": 0,
        "development_role_count": 0,
        "total_entries": 0,
        "with_instructions": 0,
        "without_instructions": 0,
        "with_capability_profile": 0,
        "with_boundary_statement": 0,
        "with_allowed_tools": 0,
        "with_success_metrics": 0,
        "with_probation_status": 0,
        "with_version_field": 0,
        "probation_status_breakdown": {
            "probation": 0,
            "promoted": 0,
            "shelved": 0,
            "unset": 0,
            "other": 0,
        },
        "probation_status_breakdown_by_shelf": {
            "business_area": {
                "probation": 0,
                "promoted": 0,
                "shelved": 0,
                "unset": 0,
                "other": 0,
            },
            "development_role": {
                "probation": 0,
                "promoted": 0,
                "shelved": 0,
                "unset": 0,
                "other": 0,
            },
        },
        "with_instructions_by_shelf": {
            "business_area": 0,
            "development_role": 0,
        },
        "without_instructions_by_shelf": {
            "business_area": 0,
            "development_role": 0,
        },
        "without_capability_profile": 0,
        "without_capability_profile_by_shelf": {
            "business_area": 0,
            "development_role": 0,
        },
        "with_capability_profile_by_shelf": {
            "business_area": 0,
            "development_role": 0,
        },
        "with_boundary_statement_by_shelf": {
            "business_area": 0,
            "development_role": 0,
        },
        "with_allowed_tools_by_shelf": {
            "business_area": 0,
            "development_role": 0,
        },
        "with_success_metrics_by_shelf": {
            "business_area": 0,
            "development_role": 0,
        },
        "with_version_field_by_shelf": {
            "business_area": 0,
            "development_role": 0,
        },
        "with_probation_status_by_shelf": {
            "business_area": 0,
            "development_role": 0,
        },
        "empty_or_missing_id_count": 0,
        "nonblank_display_name_duplicate_row_count": 0,
        "nonblank_persona_id_duplicate_row_count": 0,
        "probation_status_breakdown_other_examples": [],
        "probation_status_breakdown_other_examples_by_shelf": {
            "business_area": [],
            "development_role": [],
        },
    }
    bd = summary["probation_status_breakdown"]
    bd_by_shelf = summary["probation_status_breakdown_by_shelf"]
    wi_by_shelf = summary["with_instructions_by_shelf"]
    wo_by_shelf = summary["without_instructions_by_shelf"]
    wo_cp_by_shelf = summary["without_capability_profile_by_shelf"]
    wcp_by_shelf = summary["with_capability_profile_by_shelf"]
    wbs_by_shelf = summary["with_boundary_statement_by_shelf"]
    wat_by_shelf = summary["with_allowed_tools_by_shelf"]
    wsm_by_shelf = summary["with_success_metrics_by_shelf"]
    wvf_by_shelf = summary["with_version_field_by_shelf"]
    wps_by_shelf = summary["with_probation_status_by_shelf"]
    other_examples: set[str] = set()
    other_by_shelf: dict[str, set[str]] = {
        "business_area": set(),
        "development_role": set(),
    }
    for shelf_key in ("business_area", "development_role"):
        entries = catalog.get(shelf_key)
        if not isinstance(entries, list):
            continue
        dict_rows = [e for e in entries if isinstance(e, dict)]
        summary[f"{shelf_key}_count"] = len(dict_rows)
        summary["total_entries"] += len(dict_rows)
        for e in dict_rows:
            instr = e.get("instructions")
            if isinstance(instr, str) and instr.strip():
                summary["with_instructions"] += 1
                wi_by_shelf[shelf_key] += 1
            else:
                summary["without_instructions"] += 1
                wo_by_shelf[shelf_key] += 1
            cp = e.get("capability_profile")
            if isinstance(cp, str) and cp.strip():
                summary["with_capability_profile"] += 1
                wcp_by_shelf[shelf_key] += 1
            else:
                summary["without_capability_profile"] += 1
                wo_cp_by_shelf[shelf_key] += 1
            if str(e.get("boundary_statement") or "").strip():
                summary["with_boundary_statement"] += 1
                wbs_by_shelf[shelf_key] += 1
            at = e.get("allowed_tools")
            if isinstance(at, list) and len(at) > 0:
                summary["with_allowed_tools"] += 1
                wat_by_shelf[shelf_key] += 1
            sm = e.get("success_metrics")
            if isinstance(sm, list) and len(sm) > 0:
                summary["with_success_metrics"] += 1
                wsm_by_shelf[shelf_key] += 1
            shelf_bd = bd_by_shelf[shelf_key]
            raw_ps = str(e.get("probation_status") or "").strip()
            if raw_ps:
                summary["with_probation_status"] += 1
                wps_by_shelf[shelf_key] += 1
                low = raw_ps.lower()
                if low == "probation":
                    bd["probation"] += 1
                    shelf_bd["probation"] += 1
                elif low == "promoted":
                    bd["promoted"] += 1
                    shelf_bd["promoted"] += 1
                elif low == "shelved":
                    bd["shelved"] += 1
                    shelf_bd["shelved"] += 1
                else:
                    bd["other"] += 1
                    shelf_bd["other"] += 1
                    other_examples.add(raw_ps)
                    other_by_shelf[shelf_key].add(raw_ps)
            else:
                bd["unset"] += 1
                shelf_bd["unset"] += 1
            ver = e.get("version")
            if ver is not None and str(ver).strip() != "":
                summary["with_version_field"] += 1
                wvf_by_shelf[shelf_key] += 1
            pid = e.get("id")
            if not (isinstance(pid, str) and pid.strip()):
                summary["empty_or_missing_id_count"] += 1
    summary["probation_status_breakdown_other_examples"] = sorted(other_examples)[:10]
    ob_shelf = summary["probation_status_breakdown_other_examples_by_shelf"]
    for sk in ("business_area", "development_role"):
        ob_shelf[sk] = sorted(other_by_shelf[sk])[:10]
    dn_key_counts: Counter[str] = Counter()
    for shelf_key in ("business_area", "development_role"):
        entries = catalog.get(shelf_key)
        if not isinstance(entries, list):
            continue
        for e in entries:
            if not isinstance(e, dict):
                continue
            dn = e.get("display_name")
            if isinstance(dn, str) and dn.strip():
                dn_key_counts[dn.strip().casefold()] += 1
    summary["nonblank_display_name_duplicate_row_count"] = sum(
        n for n in dn_key_counts.values() if n > 1
    )
    id_key_counts: Counter[str] = Counter()
    for shelf_key in ("business_area", "development_role"):
        entries = catalog.get(shelf_key)
        if not isinstance(entries, list):
            continue
        for e in entries:
            if not isinstance(e, dict):
                continue
            pid = e.get("id")
            if isinstance(pid, str) and pid.strip():
                id_key_counts[pid.strip()] += 1
    summary["nonblank_persona_id_duplicate_row_count"] = sum(
        n for n in id_key_counts.values() if n > 1
    )
    return summary


def persona_catalog_operator_summary_export_json(
    summary: Mapping[str, Any] | None,
) -> str:
    return mapping_export_json(summary)


def _persona_operator_summary_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def persona_catalog_operator_summary_table_rows(
    summary: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    return mapping_to_sorted_table_rows(summary, _persona_operator_summary_cell)



def persona_catalog_operator_summary_table_rows_csv(
    summary: Mapping[str, Any] | None,
) -> str:
    rows = persona_catalog_operator_summary_table_rows(summary)
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_PERSONA_OPERATOR_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()



