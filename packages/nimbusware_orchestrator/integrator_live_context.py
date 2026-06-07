"""Extract integrator live-path signals from run event rows."""

from __future__ import annotations

from typing import Any


def integration_adapter_http_probe_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the latest ``http_probe`` payload from integration adapter writer metadata."""
    probe: dict[str, Any] | None = None
    for row in rows:
        meta = row.get("metadata") or {}
        iaw = meta.get("integration_adapter_writer")
        if not isinstance(iaw, dict):
            continue
        http_probe = iaw.get("http_probe")
        if isinstance(http_probe, dict):
            probe = http_probe
    if probe is None:
        return None
    return {
        "reachable": probe.get("reachable"),
        "status_code": probe.get("status_code"),
        "ok": probe.get("ok"),
        "content_type": probe.get("content_type"),
        "body_preview": probe.get("body_preview"),
        "attempts": probe.get("attempts"),
    }


def integrator_live_context_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize live integrator adapter I/O for gate metadata."""
    ctx: dict[str, Any] = {}
    for row in rows:
        meta = row.get("metadata") or {}
        iaw = meta.get("integration_adapter_writer")
        if not isinstance(iaw, dict):
            continue
        kind = iaw.get("target_adapter_kind")
        if kind:
            ctx["target_adapter_kind"] = kind
        status = iaw.get("target_integration_status") or iaw.get("scaffold_status")
        if status:
            ctx["adapter_integration_status"] = status
        if iaw.get("target_connected") is True:
            ctx["target_connected"] = True
    probe = integration_adapter_http_probe_from_rows(rows)
    if probe is not None:
        ctx["http_probe"] = probe
    return ctx
