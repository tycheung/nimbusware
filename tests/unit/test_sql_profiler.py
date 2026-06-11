from __future__ import annotations

import os
from pathlib import Path

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.sql_profiler import (
    check_runtime_sql_budget,
    record_sql_query,
    reset_sql_query_counter,
    run_sql_profiler_summary,
    scan_sql_query_hotspots,
)


def test_record_sql_query_session_counter() -> None:
    reset_sql_query_counter()
    assert record_sql_query() == 1
    assert record_sql_query(count=2) == 3


def test_runtime_budget_uses_session() -> None:
    reset_sql_query_counter()
    record_sql_query(count=4)
    os.environ["NIMBUSWARE_SQL_QUERY_COUNT_MAX"] = "3"
    try:
        code, msg, meta = check_runtime_sql_budget()
        assert code == 1
        assert meta["sql_query_count"] == 4
    finally:
        os.environ.pop("NIMBUSWARE_SQL_QUERY_COUNT_MAX", None)
        reset_sql_query_counter()


def test_sql_profiler_summary_includes_static() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    summary = run_sql_profiler_summary(root)
    assert "sql_profiler_exit" in summary
    assert "sql_static_hotspot_count" in summary


def test_scan_sql_hotspots_on_repo() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    code, _msg, findings = scan_sql_query_hotspots(root, max_findings=5)
    assert code in (0, 1)
    assert isinstance(findings, list)
