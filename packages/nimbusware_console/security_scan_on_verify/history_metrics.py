from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any


def security_scan_category_severity_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    legs: list[str] = []
    cat = summary.get("category")
    if isinstance(cat, str):
        c = cat.strip()
        if c:
            legs.append(f"category {c}")
    sev = summary.get("severity")
    if isinstance(sev, str):
        s = sev.strip()
        if s:
            legs.append(f"severity {s}")
    if not legs:
        return None
    return "Security scan finding: " + ", ".join(legs) + "."


def security_scan_snippet_length_caption(summary: Mapping[str, Any] | None) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    sn = summary.get("security_scan_snippet")
    if not isinstance(sn, str):
        return None
    stripped = sn.strip()
    if not stripped:
        return None
    return f"Security scan snippet (timeline): **{len(stripped)}** non-whitespace character(s)."


def security_scan_snippet_line_count_caption(summary: Mapping[str, Any] | None) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    sn = summary.get("security_scan_snippet")
    if not isinstance(sn, str):
        return None
    stripped = sn.strip()
    if not stripped:
        return None
    n = len(stripped.splitlines())
    if n < 1:
        return None
    return f"Security scan snippet (timeline): **{n}** line(s)."


def security_scan_finding_event_ids_caption(summary: Mapping[str, Any] | None) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    legs: list[str] = []
    fid = summary.get("finding_id")
    if isinstance(fid, str) and fid.strip():
        legs.append("finding_id present")
    eid = summary.get("event_id")
    if isinstance(eid, str) and eid.strip():
        legs.append("event_id present")
    if not legs:
        return None
    return "Security scan summary: " + ", ".join(legs) + "."


def security_scan_occurred_at_age_caption(summary: Mapping[str, Any] | None) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    raw = summary.get("occurred_at")
    if not isinstance(raw, str) or not raw.strip():
        return None
    stripped = raw.strip()
    normalised = stripped[:-1] + "+00:00" if stripped.endswith("Z") else stripped
    try:
        parsed = datetime.fromisoformat(normalised)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    age = int((datetime.now(timezone.utc) - parsed).total_seconds())
    if age < 0:
        return None
    return f"Security scan summary **occurred_at** age: **{age}** s (relative to UTC now)."


def security_scan_linter_nonzero_caption(summary: Mapping[str, Any] | None) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    hints: list[str] = []
    ruff = summary.get("security_scan_ruff_exit")
    if isinstance(ruff, int) and ruff != 0:
        hints.append(f"**Ruff** exit `{ruff}` (non-zero).")
    bandit = summary.get("security_scan_bandit_exit")
    if isinstance(bandit, int) and bandit != 0:
        hints.append(f"**Bandit** exit `{bandit}` (non-zero).")
    if not hints:
        return None
    tail = (
        "Review snippet and finding fields above; cross-check **Security scan metadata on "
        "verify** under Module Integrator (workflow + ``HERMES_ATTACH_SECURITY_SCAN_METADATA``)."
    )
    return " ".join(hints) + " " + tail

