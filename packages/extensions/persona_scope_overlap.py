from __future__ import annotations

from typing import Any


def _scope_in_set(entry: dict[str, Any] | None) -> set[str]:
    if not isinstance(entry, dict):
        return set()
    raw = entry.get("scope_in")
    if not isinstance(raw, list):
        return set()
    return {str(x).strip().lower() for x in raw if str(x).strip()}


def scope_in_overlaps_for_assignment(
    *,
    shelf: Any,
    persona_assignment: dict[str, Any] | None,
) -> list[str]:
    """Detect overlapping ``scope_in`` between assigned business_area and development_role."""
    if shelf is None or not isinstance(persona_assignment, dict):
        return []

    def _slot_id(raw: object) -> str | None:
        if isinstance(raw, str):
            s = raw.strip()
            return s or None
        if isinstance(raw, dict):
            val = raw.get("id") or raw.get("persona_id")
            if val is not None:
                s = str(val).strip()
                return s or None
        return None

    ba_id = _slot_id(persona_assignment.get("business_area"))
    dr_id = _slot_id(persona_assignment.get("development_role"))
    if not ba_id or not dr_id:
        return []
    ba_entry = shelf.find_entry("business_area", ba_id)
    dr_entry = shelf.find_entry("development_role", dr_id)
    ba_scope = _scope_in_set(ba_entry)
    dr_scope = _scope_in_set(dr_entry)
    overlap = sorted(ba_scope & dr_scope)
    if not overlap:
        return []
    joined = ", ".join(overlap[:5])
    suffix = f" (+{len(overlap) - 5} more)" if len(overlap) > 5 else ""
    return [f"scope_in overlap between {ba_id} and {dr_id}: {joined}{suffix}"]


def persona_scope_overlap_report(shelf: Any) -> list[dict[str, Any]]:
    """All business_area × development_role pairs with non-empty ``scope_in`` intersection."""
    if shelf is None:
        return []
    rows: list[dict[str, Any]] = []
    for ba in shelf.list_personas("business_area"):
        if not isinstance(ba, dict):
            continue
        ba_id = str(ba.get("id", "")).strip()
        if not ba_id:
            continue
        ba_scope = _scope_in_set(ba)
        for dr in shelf.list_personas("development_role"):
            if not isinstance(dr, dict):
                continue
            dr_id = str(dr.get("id", "")).strip()
            if not dr_id:
                continue
            dr_scope = _scope_in_set(dr)
            overlap = sorted(ba_scope & dr_scope)
            if not overlap:
                continue
            rows.append(
                {
                    "business_area_id": ba_id,
                    "development_role_id": dr_id,
                    "overlap_tags": overlap,
                    "overlap_count": len(overlap),
                },
            )
    rows.sort(
        key=lambda r: (
            -int(r.get("overlap_count", 0)),
            str(r.get("business_area_id", "")),
            str(r.get("development_role_id", "")),
        ),
    )
    return rows
