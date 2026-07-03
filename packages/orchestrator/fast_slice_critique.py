from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from agent_core.models import Severity
from env.env_flags import env_tri_state


def _payload(ev: dict[str, Any]) -> dict[str, Any]:
    pl = ev.get("payload")
    if isinstance(pl, dict):
        return pl
    return {}


def max_open_finding_severity(events: Sequence[dict[str, Any]]) -> Severity | None:
    order = (Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.BLOCKER)
    max_idx = -1
    for ev in events:
        if str(ev.get("event_type") or "") != "finding.created":
            continue
        pl = _payload(ev)
        raw = pl.get("severity")
        if not isinstance(raw, str):
            continue
        sev = raw.strip().upper()
        try:
            idx = order.index(Severity(sev))
        except ValueError:
            continue
        if idx > max_idx:
            max_idx = idx
    if max_idx < 0:
        return None
    return order[max_idx]


def fast_slice_skips_optional_critique_matrix(severity: Severity | None) -> bool:
    """Skip optional universal critic tail when max severity is strictly below HIGH."""
    if severity is None:
        return True
    return severity in (Severity.LOW, Severity.MEDIUM)


def fast_slice_env_effective(*, yaml_enabled: bool) -> bool:
    tri = env_tri_state("NIMBUSWARE_FAST_SLICE")
    if tri == "on":
        return True
    if tri == "off":
        return False
    return yaml_enabled
