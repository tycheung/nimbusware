"""Network/resilience static scan + SQL budget."""

from __future__ import annotations

import os
from pathlib import Path

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.network_resilience_scan import (
    check_sql_query_count_budget,
    run_network_resilience_scan_summary,
    scan_http_resilience_heuristic,
)


def test_scan_http_resilience_clean_repo() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    code, _log, findings = scan_http_resilience_heuristic(repo)
    assert isinstance(findings, list)
    assert code in (0, 1)


def test_sql_query_budget_noop_without_fixture() -> None:
    old_max = os.environ.pop("NIMBUSWARE_SQL_QUERY_COUNT_MAX", None)
    old_count = os.environ.pop("NIMBUSWARE_TEST_SQL_QUERY_COUNT", None)
    try:
        os.environ["NIMBUSWARE_SQL_QUERY_COUNT_MAX"] = "10"
        code, msg, meta = check_sql_query_count_budget()
        assert code == 0
        assert "no-op" in msg.lower() or meta.get("sql_query_count") is None
    finally:
        if old_max is not None:
            os.environ["NIMBUSWARE_SQL_QUERY_COUNT_MAX"] = old_max
        else:
            os.environ.pop("NIMBUSWARE_SQL_QUERY_COUNT_MAX", None)
        if old_count is not None:
            os.environ["NIMBUSWARE_TEST_SQL_QUERY_COUNT"] = old_count


def test_sql_query_budget_exceeded() -> None:
    os.environ["NIMBUSWARE_SQL_QUERY_COUNT_MAX"] = "5"
    os.environ["NIMBUSWARE_TEST_SQL_QUERY_COUNT"] = "9"
    try:
        code, msg, meta = check_sql_query_count_budget()
        assert code == 1
        assert meta["sql_query_count"] == 9
        assert "exceeded" in msg
    finally:
        os.environ.pop("NIMBUSWARE_SQL_QUERY_COUNT_MAX", None)
        os.environ.pop("NIMBUSWARE_TEST_SQL_QUERY_COUNT", None)


def test_run_network_resilience_scan_summary_shape() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    summary = run_network_resilience_scan_summary(repo)
    assert "network_resilience_exit" in summary
    assert "http_resilience_exit" in summary
