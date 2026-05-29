"""Static network/resilience scans + optional SQL query budget."""

from __future__ import annotations

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
    """Optional runtime hook (delegates to ``sql_profiler``)."""
    from hermes_orchestrator.sql_profiler import check_runtime_sql_budget

    return check_runtime_sql_budget()


def run_network_resilience_scan_summary(workspace: Path) -> dict[str, Any]:
    from hermes_orchestrator.sql_profiler import run_sql_profiler_summary

    http_code, http_log, http_findings = scan_http_resilience_heuristic(workspace)
    sql_prof = run_sql_profiler_summary(workspace)
    sql_code = int(sql_prof.get("sql_query_budget_exit", 0))
    static_code = int(sql_prof.get("sql_profiler_exit", 0))
    worst = max(http_code, static_code)
    return {
        "network_resilience_exit": worst,
        "http_resilience_exit": http_code,
        "http_resilience_findings": http_findings,
        "sql_query_budget_exit": sql_code,
        "network_resilience_snippet": "\n".join(
            (http_log + str(sql_prof.get("sql_profiler_snippet", ""))).splitlines()[:30],
        ),
        **{k: v for k, v in sql_prof.items() if k != "sql_profiler_snippet"},
    }
