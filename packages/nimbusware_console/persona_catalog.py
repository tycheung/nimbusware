"""Persona shelves preview for the operator console.

Uses the same YAML and validation as **GET /v1/personas** (``PersonaShelf`` under the
resolved repo root). Read-only; no HTTP call required for local operators.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import Any


def load_persona_shelves_catalog(repo_root: Path) -> dict[str, Any]:
    """Load persona shelves from Postgres (DB mode) or ``configs/personas/shelves.yaml``."""
    from nimbusware_config.persist import load_persona_shelf
    from nimbusware_console.config_materializer import console_config_materializer

    mat = console_config_materializer(repo_root)
    shelf = load_persona_shelf(repo_root, materializer=mat)
    shelf.validate_structure()
    return shelf.to_public_catalog()


def persona_catalog_flat_rows(catalog: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Flatten ``business_area`` / ``development_role`` entries with a ``shelf`` column."""
    out: list[dict[str, Any]] = []
    for shelf_key in ("business_area", "development_role"):
        entries = catalog.get(shelf_key)
        if not isinstance(entries, list):
            continue
        for e in entries:
            if not isinstance(e, dict):
                continue
            row = dict(e)
            row["shelf"] = shelf_key
            out.append(row)
    return out


def persona_catalog_operator_summary(catalog: Mapping[str, Any]) -> dict[str, Any]:
    """Aggregate counts for operators (matches ``to_public_catalog`` list shapes)."""
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
    """Pretty JSON export of :func:`persona_catalog_operator_summary` output."""
    if not isinstance(summary, Mapping):
        return "{}"
    return json.dumps(dict(summary), indent=2, ensure_ascii=False)


def _persona_operator_summary_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def persona_catalog_operator_summary_table_rows(
    summary: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column field/value rows for operator summary export."""
    if not isinstance(summary, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for key in sorted(str(k) for k in summary.keys()):
        rows.append(
            {
                "field": key,
                "value": _persona_operator_summary_cell(summary.get(key)),
            },
        )
    return rows


_PERSONA_OPERATOR_SUMMARY_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def persona_catalog_operator_summary_table_rows_csv(
    summary: Mapping[str, Any] | None,
) -> str:
    """Serialize operator summary field/value rows to CSV (UTF-8 text)."""
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


_PERSONA_OPERATOR_SUMMARY_METRICS_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def persona_catalog_operator_summary_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Structured rollup over :func:`persona_catalog_operator_summary` output (§14 #14)."""
    metrics: dict[str, Any] = {
        "total_entries": 0,
        "business_area_count": 0,
        "development_role_count": 0,
        "without_instructions": 0,
        "empty_or_missing_id_count": 0,
        "probation_total": 0,
        "promoted_total": 0,
        "shelved_total": 0,
        "duplicate_row_signals": 0,
    }
    if not isinstance(summary, Mapping):
        return metrics

    def _int_field(key: str) -> int:
        raw = summary.get(key)
        if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
            return raw
        return 0

    metrics["total_entries"] = _int_field("total_entries")
    metrics["business_area_count"] = _int_field("business_area_count")
    metrics["development_role_count"] = _int_field("development_role_count")
    metrics["without_instructions"] = _int_field("without_instructions")
    metrics["empty_or_missing_id_count"] = _int_field("empty_or_missing_id_count")
    bd = summary.get("probation_status_breakdown")
    if isinstance(bd, dict):
        metrics["probation_total"] = _int_field_from_dict(bd, "probation")
        metrics["promoted_total"] = _int_field_from_dict(bd, "promoted")
        metrics["shelved_total"] = _int_field_from_dict(bd, "shelved")
    dup_dn = _int_field("nonblank_display_name_duplicate_row_count")
    dup_id = _int_field("nonblank_persona_id_duplicate_row_count")
    metrics["duplicate_row_signals"] = dup_dn + dup_id
    return metrics


def _int_field_from_dict(d: Mapping[str, Any], key: str) -> int:
    raw = d.get(key)
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
        return raw
    return 0


def persona_catalog_operator_summary_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    return [
        {"field": "Total entries", "value": str(metrics.get("total_entries", 0))},
        {
            "field": "Business area entries",
            "value": str(metrics.get("business_area_count", 0)),
        },
        {
            "field": "Development role entries",
            "value": str(metrics.get("development_role_count", 0)),
        },
        {
            "field": "Without instructions",
            "value": str(metrics.get("without_instructions", 0)),
        },
        {
            "field": "Empty/missing id",
            "value": str(metrics.get("empty_or_missing_id_count", 0)),
        },
        {"field": "Probation", "value": str(metrics.get("probation_total", 0))},
        {"field": "Promoted", "value": str(metrics.get("promoted_total", 0))},
        {"field": "Shelved", "value": str(metrics.get("shelved_total", 0))},
        {
            "field": "Duplicate row signals",
            "value": str(metrics.get("duplicate_row_signals", 0)),
        },
    ]


def persona_catalog_operator_summary_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON export of :func:`persona_catalog_operator_summary_operator_metrics`."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def persona_catalog_operator_summary_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize persona operator summary metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_PERSONA_OPERATOR_SUMMARY_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _PERSONA_OPERATOR_SUMMARY_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def persona_catalog_operator_summary_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption when the persona catalog has entries."""
    if not isinstance(metrics, Mapping):
        return None
    total = metrics.get("total_entries", 0)
    if not isinstance(total, int) or isinstance(total, bool) or total < 1:
        return None
    woi = metrics.get("without_instructions", 0)
    if not isinstance(woi, int) or isinstance(woi, bool):
        woi = 0
    return (
        f"Persona operator summary metrics: **{total}** entr(y/ies), "
        f"**{woi}** without instructions."
    )


def persona_catalog_operator_summary_operator_metrics_export_filename_slug() -> str:
    """Stable slug for persona operator summary metrics downloads."""
    return "persona_operator_summary_metrics"


def persona_catalog_without_instructions_caption(
    operator_summary: Mapping[str, Any] | None,
) -> str | None:
    """One-line ``without_instructions`` tally from :func:`persona_catalog_operator_summary`."""
    if not isinstance(operator_summary, Mapping):
        return None
    raw = operator_summary.get("without_instructions")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    if raw == 0:
        return None
    total = operator_summary.get("total_entries")
    if isinstance(total, int) and not isinstance(total, bool) and total > 0:
        return (
            f"Personas without instructions: **{raw}** of **{total}** catalog row(s)."
        )
    return f"Personas without instructions: **{raw}** catalog row(s)."


def persona_catalog_without_capability_profile_caption(
    operator_summary: Mapping[str, Any] | None,
) -> str | None:
    """One-line ``without_capability_profile`` tally from operator summary."""
    if not isinstance(operator_summary, Mapping):
        return None
    raw = operator_summary.get("without_capability_profile")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    if raw == 0:
        return None
    total = operator_summary.get("total_entries")
    if isinstance(total, int) and not isinstance(total, bool) and total > 0:
        return (
            f"Personas without capability_profile: **{raw}** of **{total}** row(s)."
        )
    return f"Personas without capability_profile: **{raw}** row(s)."


def persona_catalog_probation_breakdown_caption(
    operator_summary: Mapping[str, Any] | None,
) -> str | None:
    """One-line probation_status tally from :func:`persona_catalog_operator_summary`."""
    if not isinstance(operator_summary, Mapping):
        return None
    bd = operator_summary.get("probation_status_breakdown")
    if not isinstance(bd, Mapping):
        return None
    promoted = int(bd.get("promoted", 0) or 0)
    probation = int(bd.get("probation", 0) or 0)
    shelved = int(bd.get("shelved", 0) or 0)
    unset = int(bd.get("unset", 0) or 0)
    other = int(bd.get("other", 0) or 0)
    total = promoted + probation + shelved + unset + other
    if total == 0:
        return None
    with_ps = operator_summary.get("with_probation_status")
    ps_note = ""
    if isinstance(with_ps, int) and not isinstance(with_ps, bool):
        ps_note = f"; {with_ps} row(s) with explicit probation_status"
    return (
        f"Probation breakdown: promoted={promoted}, probation={probation}, "
        f"shelved={shelved}, unset={unset}, other={other}{ps_note}."
    )


def persona_catalog_persona_id_duplicates_operator_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """Hint when multiple rows share the same non-blank ``id`` string."""
    if not isinstance(summary, Mapping):
        return None
    n = summary.get("nonblank_persona_id_duplicate_row_count")
    if not isinstance(n, int) or n < 1:
        return None
    return (
        "Duplicate ``id`` values: **"
        f"{n}"
        "** extra row(s) beyond the first occurrence per non-blank ``id`` "
        "(case-sensitive; see operator summary JSON)."
    )


def persona_catalog_display_name_length_caption(catalog: Mapping[str, Any] | None) -> str | None:
    """Min/max ``display_name`` character lengths for entries with non-empty names."""
    if not isinstance(catalog, Mapping):
        return None
    lengths: list[int] = []
    for shelf_key in ("business_area", "development_role"):
        entries = catalog.get(shelf_key)
        if not isinstance(entries, list):
            continue
        for e in entries:
            if not isinstance(e, dict):
                continue
            dn = e.get("display_name")
            if isinstance(dn, str) and dn.strip():
                lengths.append(len(dn.strip()))
    if not lengths:
        return None
    lo, hi = min(lengths), max(lengths)
    n = len(lengths)
    return (
        "Persona ``display_name`` lengths (chars): min **"
        f"{lo}**, max **{hi}**, across **{n}** entries with non-empty names."
    )


def persona_catalog_persona_id_length_caption(catalog: Mapping[str, Any] | None) -> str | None:
    """Min/max ``id`` string lengths for entries with non-empty ids."""
    if not isinstance(catalog, Mapping):
        return None
    lengths: list[int] = []
    for shelf_key in ("business_area", "development_role"):
        entries = catalog.get(shelf_key)
        if not isinstance(entries, list):
            continue
        for e in entries:
            if not isinstance(e, dict):
                continue
            pid = e.get("id")
            if isinstance(pid, str) and pid.strip():
                lengths.append(len(pid.strip()))
    if not lengths:
        return None
    lo, hi = min(lengths), max(lengths)
    n = len(lengths)
    return (
        "Persona ``id`` lengths (chars): min **"
        f"{lo}**, max **{hi}**, across **{n}** entries with non-empty ids."
    )


def persona_catalog_display_name_duplicates_operator_caption(
    operator_summary: Mapping[str, Any] | None,
) -> str | None:
    """Surface when multiple shelf rows reuse the same non-empty ``display_name`` string."""
    if not isinstance(operator_summary, Mapping):
        return None
    n = operator_summary.get("nonblank_display_name_duplicate_row_count")
    if not isinstance(n, int) or isinstance(n, bool) or n < 2:
        return None
    return (
        f"Operator note: **{n}** shelf entr(y/ies) share a non-empty ``display_name`` "
        "with at least one other entry (case-insensitive match after trim)."
    )


def persona_catalog_empty_id_operator_caption(
    operator_summary: Mapping[str, Any] | None,
) -> str | None:
    """Warn when shelf entries lack a non-empty string ``id``.

    Uses :func:`persona_catalog_operator_summary`.
    """
    if not isinstance(operator_summary, Mapping):
        return None
    n = operator_summary.get("empty_or_missing_id_count")
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        return None
    return (
        f"Operator note: **{n}** shelf entr(y/ies) have an empty or missing ``id`` string "
        "(``create_run`` requires valid persona ids when referenced)."
    )


def persona_catalog_taxonomy_scope_frozen_caption() -> str:
    """Lane A scope freeze for §14 #14 — two-shelf taxonomy only."""
    return (
        "Persona taxonomy scope (frozen v1): **business_area** + **development_role** "
        "shelves only — broader taxonomy expansion is deferred; use probation filters "
        "and operator metrics for shelf hygiene."
    )


def persona_catalog_critique_pairings_total_caption(
    critique_summary: Mapping[str, Any] | None,
) -> str | None:
    """One-line critic-role entry total from :func:`critique_pairings_operator_summary`."""
    if not isinstance(critique_summary, Mapping):
        return None
    if critique_summary.get("has_critique_pairings_yaml") is not True:
        return None
    if isinstance(critique_summary.get("load_error"), str) and str(
        critique_summary.get("load_error"),
    ).strip():
        return None
    raw = critique_summary.get("critique_pairing_critic_role_entries_total")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return f"Critique pairings: **{raw}** critic-role entries across producers."


def critique_pairings_operator_summary(repo_root: Path) -> dict[str, Any]:
    """Read-only peek at ``configs/personas/critique_pairings.yaml``."""
    import yaml

    from hermes_orchestrator.merge import load_yaml

    rel = "configs/personas/critique_pairings.yaml"
    path = repo_root / "configs" / "personas" / "critique_pairings.yaml"
    out: dict[str, Any] = {
        "has_critique_pairings_yaml": path.is_file(),
        "critique_pairings_yaml_relpath": rel if path.is_file() else None,
        "version": None,
        "producer_taxonomy_key_count": 0,
        "producer_taxonomy_keys": [],
        "producer_taxonomy_keys_sample": [],
        "critique_pairing_critic_role_entries_total": 0,
        "critique_pairing_critic_counts_by_producer": [],
        "critique_pairing_critic_counts_by_producer_sample": [],
        "load_error": None,
    }
    if not path.is_file():
        return out
    try:
        doc = load_yaml(path)
    except (OSError, ValueError, UnicodeDecodeError, yaml.YAMLError) as exc:
        out["load_error"] = str(exc)
        return out
    if not isinstance(doc, dict):
        out["load_error"] = "root is not a mapping"
        return out
    ver = doc.get("version")
    if type(ver) is int:
        out["version"] = ver
    elif isinstance(ver, str) and ver.strip():
        out["version"] = ver.strip()
    raw_p = doc.get("pairings")
    if not isinstance(raw_p, dict):
        out["load_error"] = "pairings is not a mapping"
        return out
    excluded_producers = {"agent_evaluator"}
    keys = sorted(
        str(k) for k in raw_p if isinstance(k, str) and str(k) not in excluded_producers
    )
    out["producer_taxonomy_key_count"] = len(keys)
    out["producer_taxonomy_keys"] = keys
    out["producer_taxonomy_keys_sample"] = keys[:12]
    total_entries = 0
    per_rows: list[dict[str, str]] = []
    for pk in keys:
        raw_val = raw_p.get(pk)
        if not isinstance(raw_val, list):
            continue
        n = sum(1 for x in raw_val if isinstance(x, str) and str(x).strip())
        total_entries += n
        per_rows.append({"producer": pk, "critic_roles": str(n)})
    out["critique_pairing_critic_role_entries_total"] = total_entries
    out["critique_pairing_critic_counts_by_producer"] = per_rows
    out["critique_pairing_critic_counts_by_producer_sample"] = per_rows[:12]
    return out


def persona_probation_other_examples_by_shelf_table_rows(
    operator_summary: Mapping[str, Any],
) -> list[dict[str, str]]:
    """Build Streamlit table rows from ``probation_status_breakdown_other_examples_by_shelf``."""
    raw = operator_summary.get("probation_status_breakdown_other_examples_by_shelf")
    if not isinstance(raw, dict):
        return []
    out: list[dict[str, str]] = []
    for shelf in sorted(str(k) for k in raw.keys()):
        ex = raw.get(shelf)
        if not isinstance(ex, list) or not ex:
            continue
        usable = [str(x).strip() for x in ex if isinstance(x, str) and str(x).strip()]
        if not usable:
            continue
        out.append(
            {
                "shelf": shelf,
                "other_probation_status_examples": ", ".join(usable),
            },
        )
    return out


_PROBATION_OTHER_BY_SHELF_CSV_COLUMNS: tuple[str, ...] = (
    "shelf",
    "other_probation_status_examples",
)


def persona_probation_other_by_shelf_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    """Pretty JSON for probation-other-by-shelf table rows (operator download)."""
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, Mapping):
            out.append(dict(r))
    return json.dumps(out, indent=2, ensure_ascii=False)


def persona_probation_other_by_shelf_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize probation-other-by-shelf rows to CSV (UTF-8 text)."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_PROBATION_OTHER_BY_SHELF_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _PROBATION_OTHER_BY_SHELF_CSV_COLUMNS})
    return buf.getvalue()


def persona_probation_other_export_filename_slug() -> str:
    """Filename slug prefix for probation-other-by-shelf exports."""
    return "persona_probation_other"


def critique_pairings_operator_summary_export_json(
    summary: Mapping[str, Any],
) -> str:
    """Pretty JSON for critique_pairings operator summary (operator download)."""
    if not isinstance(summary, Mapping):
        return "{}"
    return json.dumps(dict(summary), indent=2, ensure_ascii=False)


def critique_pairings_operator_summary_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Structured rollup over :func:`critique_pairings_operator_summary` (§14 #14)."""
    metrics: dict[str, Any] = {
        "has_critique_pairings_yaml": False,
        "producer_taxonomy_key_count": 0,
        "critic_role_entries_total": 0,
        "load_error_present": False,
    }
    if not isinstance(summary, Mapping):
        return metrics
    metrics["has_critique_pairings_yaml"] = summary.get("has_critique_pairings_yaml") is True
    pk = summary.get("producer_taxonomy_key_count")
    if isinstance(pk, int) and not isinstance(pk, bool) and pk >= 0:
        metrics["producer_taxonomy_key_count"] = pk
    total = summary.get("critique_pairing_critic_role_entries_total")
    if isinstance(total, int) and not isinstance(total, bool) and total >= 0:
        metrics["critic_role_entries_total"] = total
    err = summary.get("load_error")
    metrics["load_error_present"] = isinstance(err, str) and bool(err.strip())
    return metrics


def critique_pairings_operator_summary_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {
            "field": "Critique pairings YAML present",
            "value": str(metrics.get("has_critique_pairings_yaml", False)).lower(),
        },
        {
            "field": "Producer taxonomy keys",
            "value": str(metrics.get("producer_taxonomy_key_count", 0)),
        },
        {
            "field": "Critic role entries total",
            "value": str(metrics.get("critic_role_entries_total", 0)),
        },
    ]
    if metrics.get("load_error_present") is True:
        rows.append({"field": "Load error", "value": "yes"})
    return rows


def critique_pairings_operator_summary_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON export of critique pairings operator summary metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def critique_pairings_operator_summary_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize critique pairings operator summary metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_PERSONA_OPERATOR_SUMMARY_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _PERSONA_OPERATOR_SUMMARY_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def critique_pairings_operator_summary_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption when critique_pairings YAML is present."""
    if not isinstance(metrics, Mapping):
        return None
    if metrics.get("has_critique_pairings_yaml") is not True:
        return None
    if metrics.get("load_error_present") is True:
        return "Critique pairings operator metrics: YAML present with **load error**."
    pk = metrics.get("producer_taxonomy_key_count", 0)
    total = metrics.get("critic_role_entries_total", 0)
    if not isinstance(pk, int) or isinstance(pk, bool):
        pk = 0
    if not isinstance(total, int) or isinstance(total, bool):
        total = 0
    return (
        f"Critique pairings operator metrics: **{pk}** producer key(s), "
        f"**{total}** critic role entr(y/ies)."
    )


def critique_pairings_operator_summary_operator_metrics_export_filename_slug() -> str:
    """Stable slug for critique pairings operator summary metrics downloads."""
    return "critique_pairings_operator_summary_operator_metrics"


def critique_pairings_export_filename_slug() -> str:
    """Filename slug prefix for critique_pairings summary exports."""
    return "critique_pairings"


_CRITIQUE_PAIRINGS_CRITIC_COUNTS_CSV_COLUMNS: tuple[str, ...] = (
    "producer",
    "critic_roles",
)


def _critique_pairings_critic_counts_rows_from_list(
    raw: Any,
) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        producer = item.get("producer")
        critic_roles = item.get("critic_roles")
        if not isinstance(producer, str) or not producer.strip():
            continue
        out.append(
            {
                "producer": producer.strip(),
                "critic_roles": str(critic_roles) if critic_roles is not None else "",
            },
        )
    return out


def critique_pairings_critic_counts_table_rows(
    summary: Mapping[str, Any],
) -> list[dict[str, str]]:
    """Rows from ``critique_pairing_critic_counts_by_producer_sample``."""
    if not isinstance(summary, Mapping):
        return []
    return _critique_pairings_critic_counts_rows_from_list(
        summary.get("critique_pairing_critic_counts_by_producer_sample"),
    )


def critique_pairings_critic_counts_all_table_rows(
    summary: Mapping[str, Any],
) -> list[dict[str, str]]:
    """Rows from full ``critique_pairing_critic_counts_by_producer`` (fallback: sample)."""
    if not isinstance(summary, Mapping):
        return []
    full = summary.get("critique_pairing_critic_counts_by_producer")
    if isinstance(full, list) and full:
        return _critique_pairings_critic_counts_rows_from_list(full)
    return critique_pairings_critic_counts_table_rows(summary)


def critique_pairings_critic_counts_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    """Pretty JSON for critique pairings producer critic-count rows."""
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, Mapping):
            out.append(dict(r))
    return json.dumps(out, indent=2, ensure_ascii=False)


def critique_pairings_critic_counts_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize critique pairings critic-count rows to CSV (UTF-8 text)."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_CRITIQUE_PAIRINGS_CRITIC_COUNTS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _CRITIQUE_PAIRINGS_CRITIC_COUNTS_CSV_COLUMNS},
            )
    return buf.getvalue()


def critique_pairings_critic_counts_all_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    """Pretty JSON for full critique pairings producer critic-count rows."""
    return critique_pairings_critic_counts_export_json(rows)


def critique_pairings_critic_counts_all_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize full critique pairings critic-count rows to CSV."""
    return critique_pairings_critic_counts_table_rows_csv(rows)


_CRITIQUE_PAIRINGS_PRODUCER_KEYS_CSV_COLUMNS: tuple[str, ...] = ("producer_key",)


def _critique_pairings_producer_keys_rows_from_list(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for key in raw:
        if isinstance(key, str) and key.strip():
            out.append({"producer_key": key.strip()})
    return out


def critique_pairings_producer_keys_table_rows(
    summary: Mapping[str, Any],
) -> list[dict[str, str]]:
    """Rows from ``producer_taxonomy_keys_sample`` (order preserved)."""
    if not isinstance(summary, Mapping):
        return []
    return _critique_pairings_producer_keys_rows_from_list(
        summary.get("producer_taxonomy_keys_sample"),
    )


def critique_pairings_producer_keys_all_table_rows(
    summary: Mapping[str, Any],
) -> list[dict[str, str]]:
    """Rows from full ``producer_taxonomy_keys`` (fallback: sample)."""
    if not isinstance(summary, Mapping):
        return []
    full = summary.get("producer_taxonomy_keys")
    if isinstance(full, list) and full:
        return _critique_pairings_producer_keys_rows_from_list(full)
    return critique_pairings_producer_keys_table_rows(summary)


def critique_pairings_producer_keys_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    """Pretty JSON for critique pairings producer key sample rows."""
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, Mapping):
            out.append(dict(r))
    return json.dumps(out, indent=2, ensure_ascii=False)


def critique_pairings_producer_keys_all_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    """Pretty JSON for full critique pairings producer key rows."""
    return critique_pairings_producer_keys_export_json(rows)


def critique_pairings_producer_keys_all_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize full producer key rows to CSV."""
    return critique_pairings_producer_keys_table_rows_csv(rows)


def critique_pairings_producer_keys_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize producer key rows to CSV (UTF-8 text)."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_CRITIQUE_PAIRINGS_PRODUCER_KEYS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _CRITIQUE_PAIRINGS_PRODUCER_KEYS_CSV_COLUMNS},
            )
    return buf.getvalue()


def persona_catalog_distinct_allowed_tools(
    catalog: Mapping[str, Any],
    *,
    max_n: int = 50,
) -> list[str]:
    """Sorted deduped ``allowed_tools`` strings across all persona entries."""
    tools: set[str] = set()
    for row in persona_catalog_flat_rows(catalog):
        raw = row.get("allowed_tools")
        if not isinstance(raw, list):
            continue
        for t in raw:
            if isinstance(t, str):
                s = t.strip()
                if s:
                    tools.add(s)
    out = sorted(tools)
    if max_n <= 0:
        return []
    return out[:max_n]


def _row_matches_allowed_tool(row: Mapping[str, Any], tool_filter: str) -> bool:
    want = tool_filter.strip().lower()
    if not want or want == "all":
        return True
    raw = row.get("allowed_tools")
    if not isinstance(raw, list):
        return False
    for t in raw:
        if not isinstance(t, str):
            continue
        s = t.strip()
        if not s:
            continue
        sl = s.lower()
        if sl == want or want in sl:
            return True
    return False


def persona_catalog_allowed_tool_filter_caption(
    tool: str,
    *,
    match_count: int,
    total_count: int,
) -> str | None:
    """Caption when an allowed-tool filter is active (interim until persona ``tags`` schema)."""
    t = str(tool).strip()
    if not t or t.lower() == "all":
        return None
    if match_count < 0 or total_count < 0:
        return None
    return (
        f"Allowed tool filter **{t}**: **{match_count}** of **{total_count}** "
        "persona(s) match (interim until persona ``tags`` schema ships)."
    )


def filter_persona_catalog_flat_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    query: str = "",
    shelf: str | None = None,
    probation_status: str | None = None,
    allowed_tool: str | None = None,
) -> list[dict[str, Any]]:
    """Case-insensitive substring match on ``id`` / ``display_name``; optional shelf filter.

    Optional **probation_status** (fo127): ``all`` / unset keeps all rows; ``(unset)`` keeps
    rows with no ``probation_status``; otherwise match is case-insensitive on the literal
    ``probation`` / ``promoted`` / ``shelved`` values.

    Optional **allowed_tool**: ``all`` / unset keeps all rows; otherwise keep rows whose
    ``allowed_tools`` list contains the filter (exact case-insensitive match or substring).
    """
    q = str(query).strip().lower()
    want_shelf = str(shelf).strip() if shelf else ""
    ps_raw = str(probation_status).strip() if probation_status else ""
    ps_filter = ps_raw.lower()
    tool_raw = str(allowed_tool).strip() if allowed_tool else ""
    tool_filter = tool_raw.lower()
    out: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, Mapping):
            continue
        row = dict(raw)
        if want_shelf and row.get("shelf") != want_shelf:
            continue
        if ps_filter and ps_filter != "all":
            row_ps = str(row.get("probation_status") or "").strip()
            if ps_filter == "(unset)":
                if row_ps:
                    continue
            elif row_ps.lower() != ps_filter:
                continue
        if tool_filter and tool_filter != "all":
            if not _row_matches_allowed_tool(row, tool_raw):
                continue
        if q:
            ident = str(row.get("id") or "").lower()
            disp = str(row.get("display_name") or "").lower()
            if q not in ident and q not in disp:
                continue
        out.append(row)
    return out


def persona_catalog_flat_rows_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    """Serialize flat persona rows to CSV (UTF-8 text). Empty input yields header-only or empty."""
    if not rows:
        return ""
    preferred = ("shelf", "id", "display_name")
    seen: set[str] = set()
    fieldnames: list[str] = []
    for key in preferred:
        if any(key in r for r in rows if isinstance(r, Mapping)):
            fieldnames.append(key)
            seen.add(key)
    rest = sorted(
        {k for r in rows if isinstance(r, Mapping) for k in r if k not in seen},
    )
    fieldnames.extend(rest)
    buf = StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in fieldnames})
    return buf.getvalue()


def persona_catalog_flat_rows_export_json(rows: Sequence[Mapping[str, Any]]) -> str:
    """Pretty JSON for filtered flat persona table rows (operator download)."""
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, Mapping):
            out.append(dict(r))
    return json.dumps(out, indent=2, ensure_ascii=False)


def persona_catalog_flat_export_filename_slug() -> str:
    """Filename slug prefix for filtered flat persona exports (no run id on this screen)."""
    return "persona_flat"
