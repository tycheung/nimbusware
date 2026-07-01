from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

from nimbusware_console.explainer_core.display_common import stringify_display_value as _stringify


def universal_critique_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(timeline_body, Mapping):
        return None
    raw = timeline_body.get("universal_critique")
    return raw if isinstance(raw, dict) else None


def universal_critique_timeline_stage_rows(
    summary: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(summary, Mapping):
        return []
    stages = summary.get("stages")
    if not isinstance(stages, list):
        return []
    rows: list[dict[str, str]] = []
    for s in stages:
        if not isinstance(s, dict):
            continue
        rows.append(
            {
                "Stage": _stringify(s.get("stage_name")),
                "Verdict": _stringify(s.get("verdict")),
                "Failure reason": _stringify(s.get("failure_reason_code")),
                "Occurred at": _stringify(s.get("occurred_at")),
                "Event id": _stringify(s.get("event_id")),
            },
        )
    return rows


def universal_critique_timeline_fail_stage_rows(
    summary: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(summary, Mapping):
        return []
    stages = summary.get("stages")
    if not isinstance(stages, list):
        return []
    rows: list[dict[str, str]] = []
    for s in stages:
        if not isinstance(s, dict):
            continue
        verdict = s.get("verdict")
        if not isinstance(verdict, str) or verdict.strip().upper() != "FAIL":
            continue
        rows.append(
            {
                "Stage": _stringify(s.get("stage_name")),
                "Verdict": _stringify(s.get("verdict")),
                "Failure reason": _stringify(s.get("failure_reason_code")),
                "Occurred at": _stringify(s.get("occurred_at")),
                "Event id": _stringify(s.get("event_id")),
            },
        )
    return rows


_UNIVERSAL_CRITIQUE_STAGE_CSV_COLUMNS: tuple[str, ...] = (
    "Stage",
    "Verdict",
    "Failure reason",
    "Occurred at",
    "Event id",
)


def universal_critique_timeline_stage_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_UNIVERSAL_CRITIQUE_STAGE_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _UNIVERSAL_CRITIQUE_STAGE_CSV_COLUMNS},
            )
    return buf.getvalue()


def universal_critique_fail_stage_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_UNIVERSAL_CRITIQUE_STAGE_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _UNIVERSAL_CRITIQUE_STAGE_CSV_COLUMNS},
            )
    return buf.getvalue()


def universal_critique_timeline_export_json(summary: Mapping[str, Any] | None) -> str:
    if not isinstance(summary, Mapping):
        return "{}"
    return json.dumps(dict(summary), ensure_ascii=False, indent=2)


def universal_critique_timeline_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


__all__ = ("_stringify",)
