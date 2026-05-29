"""B2 promotion proof for §14 #18 — security scan tool categories on verify."""

from __future__ import annotations

from pathlib import Path

from hermes_orchestrator.security_scan import (
    SECURITY_SCAN_CATEGORIES,
    security_scan_tool_summary,
)

ROOT = Path(__file__).resolve().parents[1]


def test_security_scan_categories_include_phase3_tools() -> None:
    assert "ruff" in SECURITY_SCAN_CATEGORIES
    assert "bandit" in SECURITY_SCAN_CATEGORIES
    assert "mypy" in SECURITY_SCAN_CATEGORIES
    assert "ruff_perf" in SECURITY_SCAN_CATEGORIES
    assert "n_plus_one_heuristic" in SECURITY_SCAN_CATEGORIES


def test_security_scan_tool_summary_shape() -> None:
    summary = security_scan_tool_summary(0, 1, 2, 0, 1)
    assert summary["security_scan_tools"]["ruff"] == 0
    assert summary["security_scan_tools"]["bandit"] == 1
    assert summary["security_scan_tools"]["mypy"] == 2
    assert summary["security_scan_tools"]["n_plus_one_heuristic"] == 1
    assert len(summary["security_scan_categories"]) == 5
