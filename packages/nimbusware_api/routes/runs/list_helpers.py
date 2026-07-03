from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlencode


def _sanitize_workflow_profile_prefix(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    s = str(value).strip()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}", s):
        return None
    return s


def _runs_list_query_string(
    *,
    limit: int,
    offset: int | None,
    order: str,
    include_summary: int,
    workflow_profile: str | None,
    workflow_profile_prefix: str | None,
    created_after: str | None,
    created_before: str | None,
    has_escalation: int | None,
    cursor: str | None = None,
    list_status: str | None = None,
) -> str:
    pairs: list[tuple[str, str]] = [
        ("limit", str(limit)),
        ("order", order),
        ("include_summary", str(include_summary)),
    ]
    if offset is not None:
        pairs.insert(1, ("offset", str(offset)))
    if cursor is not None:
        pairs.append(("cursor", cursor))
    if workflow_profile is not None:
        pairs.append(("workflow_profile", workflow_profile))
    if workflow_profile_prefix is not None:
        pairs.append(("workflow_profile_prefix", workflow_profile_prefix))
    if created_after is not None:
        pairs.append(("created_after", created_after))
    if created_before is not None:
        pairs.append(("created_before", created_before))
    if has_escalation is not None:
        pairs.append(("has_escalation", str(has_escalation)))
    if list_status is not None:
        pairs.append(("status", list_status))
    return urlencode(pairs)


def _parse_query_datetime(field: str, value: str | None) -> datetime | None:
    if value is None or not str(value).strip():
        return None
    try:
        s = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
    except ValueError as exc:
        msg = f"{field} must be a valid ISO-8601 datetime"
        raise ValueError(msg) from exc
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
