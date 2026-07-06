from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from orchestrator.anti_deadlock import (
    _PROGRESS_IGNORE,
    _first_run_created_at,
    count_progress_events,
)
from unit.composite_contracts.anti_deadlock_matrix import (
    B3_AWARE_ROWS,
    B3_NAIVE_ROWS,
    COUNT_PROGRESS_IGNORE_CASES,
    COUNT_PROGRESS_MIXED_CASES,
    COUNT_PROGRESS_NON_IGNORE_CASES,
    CROSS_HELPER_CASES,
    EXPECTED_PROGRESS_IGNORE,
    FIRST_RUN_CREATED_AT_GUARD_CASES,
    FIRST_RUN_CREATED_AT_NORMALIZATION_CASES,
)
from unit.composite_contracts.matrix_runner import run_value_matrix

_UTC = timezone.utc


def _invoke_first_run_created_at(case: dict[str, Any]) -> datetime | None:
    return _first_run_created_at(case["rows"])


def _invoke_count_progress(case: dict[str, Any]) -> int:
    return count_progress_events(case["rows"])


@pytest.mark.parametrize("case", FIRST_RUN_CREATED_AT_GUARD_CASES, ids=lambda c: c["case_id"])
def test_first_run_created_at_guard_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=_invoke_first_run_created_at)


@pytest.mark.parametrize(
    "case",
    FIRST_RUN_CREATED_AT_NORMALIZATION_CASES,
    ids=lambda c: c["case_id"],
)
def test_first_run_created_at_normalization_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=_invoke_first_run_created_at)


def test_first_run_created_at_aware_naive_divergence() -> None:
    aware = _first_run_created_at(B3_AWARE_ROWS)
    naive = _first_run_created_at(B3_NAIVE_ROWS)
    assert aware == datetime(2026, 1, 1, 7, 0, tzinfo=_UTC)
    assert naive == datetime(2026, 1, 1, 12, 0, tzinfo=_UTC)
    assert aware != naive


@pytest.mark.parametrize("case", COUNT_PROGRESS_MIXED_CASES, ids=lambda c: c["case_id"])
def test_count_progress_mixed_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=_invoke_count_progress)


@pytest.mark.parametrize("case", COUNT_PROGRESS_IGNORE_CASES, ids=lambda c: c["case_id"])
def test_count_progress_ignore_members_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=_invoke_count_progress)


@pytest.mark.parametrize("case", COUNT_PROGRESS_NON_IGNORE_CASES, ids=lambda c: c["case_id"])
def test_count_progress_non_ignore_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=_invoke_count_progress)


def test_progress_ignore_frozenset_contract() -> None:
    assert isinstance(_PROGRESS_IGNORE, frozenset)
    assert _PROGRESS_IGNORE == EXPECTED_PROGRESS_IGNORE
    assert len(_PROGRESS_IGNORE) == 6


@pytest.mark.parametrize("case", CROSS_HELPER_CASES, ids=lambda c: c["case_id"])
def test_cross_helper_dual_purpose_matrix(case: dict[str, Any]) -> None:
    rows = case["rows"]
    assert _first_run_created_at(rows) == case["expected_timestamp"]
    assert count_progress_events(rows) == case["expected_progress"]
