from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from console.security_scan_on_verify.latest import (
    security_scan_on_verify_summary_rows,
)


def security_scan_metadata_timeline_workflow_alignment_caption(
    *,
    timeline_security_scan_on_verify: Mapping[str, Any] | None,
    explainer_payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(explainer_payload, Mapping):
        return None
    err = explainer_payload.get("load_error")
    if isinstance(err, str) and err.strip():
        return None
    eff = explainer_payload.get("effective_enabled")
    if not isinstance(eff, bool):
        return None
    has_scan = bool(security_scan_on_verify_summary_rows(timeline_security_scan_on_verify))
    if has_scan and not eff:
        return (
            "Timeline shows **security_scan_on_verify** scan output, but "
            "**security_scan_metadata_on_verify** is **effective false** for the selected "
            "workflow profile (YAML + ``NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA``). "
            "Cross-check **Module Integrator** > Security scan metadata on verify."
        )
    if (not has_scan) and eff:
        return (
            "Workflow enables **security_scan_metadata_on_verify** for the selected profile, "
            "but this timeline has no **security_scan_on_verify** summary (no verifier scan "
            "metadata on finding.created events yet)."
        )
    return None
