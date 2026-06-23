from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.explainer_core.operator_metrics_exports import bind_operator_metrics_exports


def persona_catalog_operator_summary_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
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


(
    persona_catalog_operator_summary_operator_metrics_export_json,
    persona_catalog_operator_summary_operator_metrics_table_rows_csv,
    persona_catalog_operator_summary_operator_metrics_export_filename_slug,
) = bind_operator_metrics_exports(export_slug="persona_operator_summary_metrics")


def persona_catalog_operator_summary_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
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


def persona_catalog_without_instructions_caption(
    operator_summary: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(operator_summary, Mapping):
        return None
    raw = operator_summary.get("without_instructions")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    if raw == 0:
        return None
    total = operator_summary.get("total_entries")
    if isinstance(total, int) and not isinstance(total, bool) and total > 0:
        return f"Personas without instructions: **{raw}** of **{total}** catalog row(s)."
    return f"Personas without instructions: **{raw}** catalog row(s)."


def persona_catalog_without_capability_profile_caption(
    operator_summary: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(operator_summary, Mapping):
        return None
    raw = operator_summary.get("without_capability_profile")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    if raw == 0:
        return None
    total = operator_summary.get("total_entries")
    if isinstance(total, int) and not isinstance(total, bool) and total > 0:
        return f"Personas without capability_profile: **{raw}** of **{total}** row(s)."
    return f"Personas without capability_profile: **{raw}** row(s)."


def persona_catalog_probation_breakdown_caption(
    operator_summary: Mapping[str, Any] | None,
) -> str | None:
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
    return (
        "Persona taxonomy scope (frozen v1): **business_area** + **development_role** "
        "shelves only — broader taxonomy expansion is deferred; use probation filters "
        "and operator metrics for shelf hygiene."
    )


def persona_catalog_critique_pairings_total_caption(
    critique_summary: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(critique_summary, Mapping):
        return None
    if critique_summary.get("has_critique_pairings_yaml") is not True:
        return None
    if (
        isinstance(critique_summary.get("load_error"), str)
        and str(
            critique_summary.get("load_error"),
        ).strip()
    ):
        return None
    raw = critique_summary.get("critique_pairing_critic_role_entries_total")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return f"Critique pairings: **{raw}** critic-role entries across producers."
