from __future__ import annotations

import os
import re
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_sql_query_count_var: ContextVar[int] = ContextVar("nimbusware_sql_query_count", default=0)

_SQL_IN_LOOP = re.compile(
    r"for\s+\w+\s+in\s+.+:\s*\n(?:.*\n){0,10}.*"
    r"(?:\.execute\(|session\.query|\.scalars\(|fetchall\(|cursor\.execute)",
    re.MULTILINE,
)

_SQL_EXECUTE_LINE = re.compile(
    r"\b(?:\.execute\(|session\.query\(|\.scalars\(|raw_connection\(\))",
)


def reset_sql_query_counter() -> None:
    _sql_query_count_var.set(0)


def record_sql_query(*, count: int = 1) -> int:
    """Hook for tests or instrumented DB layers; returns new total."""
    total = _sql_query_count_var.get() + max(0, count)
    _sql_query_count_var.set(total)
    return total


def current_sql_query_count() -> int:
    return _sql_query_count_var.get()


@dataclass
class SqlProfilerSnapshot:
    runtime_count: int | None
    budget_limit: int | None
    budget_exceeded: bool
    static_hotspot_count: int
    static_findings: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "sql_query_count": self.runtime_count,
            "sql_query_budget_limit": self.budget_limit,
            "sql_query_budget_exceeded": self.budget_exceeded,
            "sql_static_hotspot_count": self.static_hotspot_count,
            "sql_static_findings_sample": self.static_findings[:10],
        }


def scan_sql_query_hotspots(
    workspace: Path,
    *,
    max_findings: int = 25,
) -> tuple[int, str, list[str]]:
    """Static scan for query-in-loop and dense execute lines under ``packages/``."""
    root = workspace / "packages"
    if not root.is_dir():
        return 0, "sql profiler static: skipped (no packages/)\n", []
    findings: list[str] = []
    for path in root.rglob("*.py"):
        if "test" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = str(path.relative_to(workspace)).replace("\\", "/")
        for pat in (_SQL_IN_LOOP,):
            for m in pat.finditer(text):
                line = text[: m.start()].count("\n") + 1
                findings.append(f"{rel}:{line}: query-in-loop pattern")
                if len(findings) >= max_findings:
                    break
            if len(findings) >= max_findings:
                break
        if len(findings) >= max_findings:
            break
        execute_lines = sum(1 for line in text.splitlines() if _SQL_EXECUTE_LINE.search(line))
        if execute_lines > 40:
            findings.append(f"{rel}: dense SQL execute surface ({execute_lines} lines)")
            if len(findings) >= max_findings:
                break
    if not findings:
        return 0, "sql profiler static: no hotspots\n", []
    body = "\n".join(findings[:max_findings])
    return 1, f"sql profiler static ({len(findings)}):\n{body}\n", findings


def check_runtime_sql_budget() -> tuple[int, str, dict[str, Any]]:
    """Compare session counter and/or ``NIMBUSWARE_TEST_SQL_QUERY_COUNT`` to limit."""
    max_raw = os.environ.get("NIMBUSWARE_SQL_QUERY_COUNT_MAX", "").strip()
    if not max_raw:
        return 0, "sql profiler runtime: skipped (NIMBUSWARE_SQL_QUERY_COUNT_MAX unset)\n", {}
    try:
        limit = max(1, int(max_raw))
    except ValueError:
        return 0, "sql profiler runtime: invalid NIMBUSWARE_SQL_QUERY_COUNT_MAX\n", {}

    session_count = current_sql_query_count()
    env_raw = os.environ.get("NIMBUSWARE_TEST_SQL_QUERY_COUNT", "").strip()
    count: int | None = session_count if session_count > 0 else None
    if env_raw:
        try:
            count = int(env_raw)
        except ValueError:
            return 1, "sql profiler runtime: invalid NIMBUSWARE_TEST_SQL_QUERY_COUNT\n", {}

    if count is None:
        return (
            0,
            "sql profiler runtime: no session counter (use record_sql_query or env)\n",
            {"sql_query_budget_limit": limit, "sql_query_count": None},
        )

    meta = {
        "sql_query_budget_limit": limit,
        "sql_query_count": count,
        "sql_profiler_source": "session" if session_count > 0 else "env",
    }
    if count > limit:
        return (
            1,
            f"sql profiler runtime exceeded: {count} > {limit}\n",
            meta,
        )
    return 0, f"sql profiler runtime ok: {count} <= {limit}\n", meta


def run_sql_profiler_summary(workspace: Path) -> dict[str, Any]:
    """Combined static + runtime SQL profiler snapshot for P3 stages."""
    static_code, static_log, static_findings = scan_sql_query_hotspots(workspace)
    runtime_code, runtime_log, runtime_meta = check_runtime_sql_budget()
    worst = max(static_code, runtime_code)
    limit = runtime_meta.get("sql_query_budget_limit")
    count = runtime_meta.get("sql_query_count")
    snap = SqlProfilerSnapshot(
        runtime_count=count if isinstance(count, int) else None,
        budget_limit=limit if isinstance(limit, int) else None,
        budget_exceeded=runtime_code != 0,
        static_hotspot_count=len(static_findings),
        static_findings=static_findings,
    )
    return {
        "sql_profiler_exit": worst,
        "sql_profiler_snippet": "\n".join(
            (static_log + runtime_log).splitlines()[:25],
        ),
        **snap.to_metadata(),
        "sql_query_budget_exit": runtime_code,
    }
