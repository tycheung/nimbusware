"""Static network/resilience scans + optional SQL query budget (Phase 3 / fo145)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

_HTTP_CALL_PATTERNS = (
    re.compile(r"\bhttpx\.(get|post|put|patch|delete|request)\s*\("),
    re.compile(r"\bhttpx\.(Client|AsyncClient)\s*\("),
    re.compile(r"\brequests\.(get|post|put|patch|delete|request)\s*\("),
)

_TIMEOUT_HINT = re.compile(r"\btimeout\s*=")
_RETRY_HINT = re.compile(r"\b(retries|retry|Retry)\s*=")


def scan_http_resilience_heuristic(
    workspace: Path,
    *,
    max_findings: int = 25,
) -> tuple[int, str, list[str]]:
    """Flag HTTP client calls in ``packages/`` without obvious timeout/retry hints."""
    root = workspace / "packages"
    if not root.is_dir():
        return 0, "http resilience: skipped (no packages/)\n", []
    findings: list[str] = []
    for path in root.rglob("*.py"):
        if "test" in path.parts:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for idx, line in enumerate(lines, start=1):
            if not any(p.search(line) for p in _HTTP_CALL_PATTERNS):
                continue
            window = "\n".join(lines[max(0, idx - 2) : min(len(lines), idx + 2)])
            if _TIMEOUT_HINT.search(window) or _RETRY_HINT.search(window):
                continue
            rel = path.relative_to(workspace)
            findings.append(f"{rel}:{idx}: HTTP call without timeout/retry hint")
            if len(findings) >= max_findings:
                break
        if len(findings) >= max_findings:
            break
    if not findings:
        return 0, "http resilience: no missing timeout/retry hints\n", []
    body = "\n".join(findings[:max_findings])
    return 1, f"http resilience findings ({len(findings)}):\n{body}\n", findings


def check_sql_query_count_budget() -> tuple[int, str, dict[str, Any]]:
    """Optional runtime hook: compare test session counter to ``HERMES_SQL_QUERY_COUNT_MAX``."""
    max_raw = os.environ.get("HERMES_SQL_QUERY_COUNT_MAX", "").strip()
    if not max_raw:
        return 0, "sql query budget: skipped (HERMES_SQL_QUERY_COUNT_MAX unset)\n", {}
    try:
        limit = max(1, int(max_raw))
    except ValueError:
        return 0, "sql query budget: invalid HERMES_SQL_QUERY_COUNT_MAX\n", {}
    count_raw = os.environ.get("HERMES_TEST_SQL_QUERY_COUNT", "").strip()
    if not count_raw:
        return (
            0,
            "sql query budget: no HERMES_TEST_SQL_QUERY_COUNT (no-op without test fixture)\n",
            {"sql_query_budget_limit": limit, "sql_query_count": None},
        )
    try:
        count = int(count_raw)
    except ValueError:
        return 1, "sql query budget: invalid HERMES_TEST_SQL_QUERY_COUNT\n", {}
    meta = {"sql_query_budget_limit": limit, "sql_query_count": count}
    if count > limit:
        return (
            1,
            f"sql query budget exceeded: {count} > {limit}\n",
            meta,
        )
    return 0, f"sql query budget ok: {count} <= {limit}\n", meta


def run_network_resilience_scan_summary(workspace: Path) -> dict[str, Any]:
    http_code, http_log, http_findings = scan_http_resilience_heuristic(workspace)
    sql_code, sql_log, sql_meta = check_sql_query_count_budget()
    worst = max(http_code, sql_code)
    return {
        "network_resilience_exit": worst,
        "http_resilience_exit": http_code,
        "http_resilience_findings": http_findings,
        "sql_query_budget_exit": sql_code,
        "network_resilience_snippet": "\n".join(
            (http_log + sql_log).splitlines()[:30],
        ),
        **sql_meta,
    }
