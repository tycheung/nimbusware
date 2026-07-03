from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def integration_adapter_writer_from_events(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    from orchestrator.integrator.writer_stage import (
        INTEGRATION_ADAPTER_WRITER_STAGE,
    )

    for row in reversed(rows):
        if row.get("event_type") != "stage.started":
            continue
        payload = row.get("payload") or {}
        if (payload.get("stage_name") or "") != INTEGRATION_ADAPTER_WRITER_STAGE:
            continue
        meta = row.get("metadata") or {}
        iaw = meta.get("integration_adapter_writer")
        if isinstance(iaw, Mapping):
            return dict(iaw)
    return None


def integration_adapter_writer_run_table_rows(
    iaw: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(iaw, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for key, label in (
        ("scaffold_status", "Scaffold status"),
        ("target_integration_status", "Target integration"),
        ("target_adapter_kind", "Adapter kind"),
        ("workspace_manifest_path", "Manifest path"),
        ("adapter_module_path", "Adapter module"),
        ("rollback_reason", "Rollback reason"),
    ):
        val = iaw.get(key)
        if val is None or val == "":
            continue
        rows.append({"field": label, "value": str(val)})
    return rows


def integration_adapter_writer_run_caption(iaw: Mapping[str, Any] | None) -> str:
    if not isinstance(iaw, Mapping):
        return "No Integration Adapter Writer stage for this run."
    status = str(iaw.get("target_integration_status") or iaw.get("scaffold_status") or "unknown")
    kind = str(iaw.get("target_adapter_kind") or "").strip()
    prefix = f"{kind}: " if kind else ""
    return f"{prefix}Integration Adapter Writer — {status}."
