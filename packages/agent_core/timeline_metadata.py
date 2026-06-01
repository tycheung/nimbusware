"""Run.created metadata helpers shared by orchestrator, API, and projections."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _persona_slot_public(raw: object) -> dict[str, str] | None:
    if isinstance(raw, str):
        pid = raw.strip()
        return {"id": pid} if pid else None
    if isinstance(raw, dict):
        pid_raw: object | None = raw.get("id")
        if pid_raw is None:
            pid_raw = raw.get("persona_id")
        if pid_raw is not None:
            sid = str(pid_raw).strip()
            if sid:
                out: dict[str, str] = {"id": sid}
                dn = raw.get("display_name")
                if isinstance(dn, str) and dn.strip():
                    out["display_name"] = dn.strip()
                return out
    return None


def persona_assignment_from_run_created_metadata(
    metadata: Mapping[str, Any] | dict[str, Any],
) -> dict[str, Any] | None:
    """Stable persona assignment dict from ``run.created`` metadata."""
    if not isinstance(metadata, Mapping):
        return None
    pa = metadata.get("persona_assignment")
    if not isinstance(pa, Mapping):
        return None
    out: dict[str, Any] = {}
    ba = _persona_slot_public(pa.get("business_area"))
    if ba is not None:
        out["business_area"] = ba
    dr = _persona_slot_public(pa.get("development_role"))
    if dr is not None:
        out["development_role"] = dr
    return out if out else None


def critique_coverage_from_run_created_metadata(
    metadata: Mapping[str, Any] | dict[str, Any],
) -> dict[str, Any] | None:
    """Freeze-safe critique coverage from ``run.created`` metadata."""
    if not isinstance(metadata, Mapping):
        return None
    raw = metadata.get("critique_coverage")
    if not isinstance(raw, Mapping):
        return None
    out: dict[str, Any] = {}
    for key in (
        "registry_producers",
        "paired_producers",
        "unpaired_producers",
        "pairing_errors",
    ):
        val = raw.get(key)
        if isinstance(val, list):
            out[key] = list(val)
    return out if out else None


__all__ = [
    "critique_coverage_from_run_created_metadata",
    "persona_assignment_from_run_created_metadata",
]
