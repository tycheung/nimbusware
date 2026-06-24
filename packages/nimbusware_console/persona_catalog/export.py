from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

from nimbusware_console.components.operator_metrics import sequence_export_json
from nimbusware_console.persona_catalog.load import (
    persona_catalog_flat_rows,
)


def persona_catalog_distinct_allowed_tools(
    catalog: Mapping[str, Any],
    *,
    max_n: int = 50,
) -> list[str]:
    tools: set[str] = set()
    for row in persona_catalog_flat_rows(catalog):
        raw = row.get("allowed_tools")
        if not isinstance(raw, list):
            continue
        for t in raw:
            if isinstance(t, str):
                s = t.strip()
                if s:
                    tools.add(s)
    out = sorted(tools)
    if max_n <= 0:
        return []
    return out[:max_n]


def _row_matches_allowed_tool(row: Mapping[str, Any], tool_filter: str) -> bool:
    want = tool_filter.strip().lower()
    if not want or want == "all":
        return True
    raw = row.get("allowed_tools")
    if not isinstance(raw, list):
        return False
    for t in raw:
        if not isinstance(t, str):
            continue
        s = t.strip()
        if not s:
            continue
        sl = s.lower()
        if sl == want or want in sl:
            return True
    return False


def persona_catalog_allowed_tool_filter_caption(
    tool: str,
    *,
    match_count: int,
    total_count: int,
) -> str | None:
    t = str(tool).strip()
    if not t or t.lower() == "all":
        return None
    if match_count < 0 or total_count < 0:
        return None
    return (
        f"Allowed tool filter **{t}**: **{match_count}** of **{total_count}** "
        "persona(s) match (interim until persona ``tags`` schema ships)."
    )


def filter_persona_catalog_flat_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    query: str = "",
    shelf: str | None = None,
    probation_status: str | None = None,
    allowed_tool: str | None = None,
) -> list[dict[str, Any]]:
    q = str(query).strip().lower()
    want_shelf = str(shelf).strip() if shelf else ""
    ps_raw = str(probation_status).strip() if probation_status else ""
    ps_filter = ps_raw.lower()
    tool_raw = str(allowed_tool).strip() if allowed_tool else ""
    tool_filter = tool_raw.lower()
    out: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, Mapping):
            continue
        row = dict(raw)
        if want_shelf and row.get("shelf") != want_shelf:
            continue
        if ps_filter and ps_filter != "all":
            row_ps = str(row.get("probation_status") or "").strip()
            if ps_filter == "(unset)":
                if row_ps:
                    continue
            elif row_ps.lower() != ps_filter:
                continue
        if tool_filter and tool_filter != "all":
            if not _row_matches_allowed_tool(row, tool_raw):
                continue
        if q:
            ident = str(row.get("id") or "").lower()
            disp = str(row.get("display_name") or "").lower()
            if q not in ident and q not in disp:
                continue
        out.append(row)
    return out


def persona_catalog_flat_rows_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return ""
    preferred = ("shelf", "id", "display_name")
    seen: set[str] = set()
    fieldnames: list[str] = []
    for key in preferred:
        if any(key in r for r in rows if isinstance(r, Mapping)):
            fieldnames.append(key)
            seen.add(key)
    rest = sorted(
        {k for r in rows if isinstance(r, Mapping) for k in r if k not in seen},
    )
    fieldnames.extend(rest)
    buf = StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in fieldnames})
    return buf.getvalue()


def persona_catalog_flat_rows_export_json(rows: Sequence[Mapping[str, Any]]) -> str:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    return sequence_export_json([dict(r) for r in rows if isinstance(r, Mapping)])


def persona_catalog_flat_export_filename_slug() -> str:
    return "persona_flat"
