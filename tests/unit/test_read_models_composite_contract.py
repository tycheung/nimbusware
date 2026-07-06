from __future__ import annotations

from typing import Any

import pytest

from projections.run_summary import (
    RUN_LIST_FILTER_STATUSES,
    build_run_summary,
    run_has_started,
)
from unit.composite_contracts.matrix_runner import (
    assert_matrix_case,
    run_exception_matrix,
    run_value_matrix,
)
from unit.composite_contracts.read_models_matrix import (
    EMPTY_SUMMARY_CASE,
    ESCALATION_FLAG_CASES,
    EVENT_COUNT_LATEST_CASES,
    FILTER_STATUS_MEMBERSHIP_CASES,
    FILTER_STATUS_TYPE_CASE,
    FINDINGS_COUNT_CASES,
    RUN_CREATED_EXTRACTION_CASES,
    RUN_HAS_STARTED_BASELINE_CASES,
    RUN_HAS_STARTED_MALFORMED_CASES,
    RUN_HAS_STARTED_POSITION_CASES,
    STATUS_LADDER_CASES,
    append_event_sequence,
    append_event_sequence_with_repeat,
)


def _rows_for(case: dict[str, Any]) -> list[dict[str, Any]]:
    if "rows" in case:
        return case["rows"]
    if "rows_builder" in case:
        return case["rows_builder"]()
    if "repeat" in case:
        kind, count = case["repeat"]
        return append_event_sequence_with_repeat(
            case["sequence"],
            repeat_kind=kind,
            repeat_count=count,
        )
    return append_event_sequence(case["sequence"])


def _invoke_summary(case: dict[str, Any]) -> dict[str, Any]:
    return build_run_summary(_rows_for(case))


def _invoke_run_has_started(case: dict[str, Any]) -> bool:
    return run_has_started(_rows_for(case))


def test_build_run_summary_empty_matrix() -> None:
    run_value_matrix((EMPTY_SUMMARY_CASE,), invoke=_invoke_summary)


@pytest.mark.parametrize("case", FILTER_STATUS_MEMBERSHIP_CASES, ids=lambda c: c["case_id"])
def test_run_list_filter_status_membership_matrix(case: dict[str, Any]) -> None:
    is_member = case["status"] in RUN_LIST_FILTER_STATUSES
    assert is_member == case["expect_member"], case["msg"]


def test_run_list_filter_status_type_matrix() -> None:
    case = FILTER_STATUS_TYPE_CASE
    assert isinstance(RUN_LIST_FILTER_STATUSES, case["expected_type"]), (
        f"A3: RUN_LIST_FILTER_STATUSES must be a frozenset; got "
        f"{type(RUN_LIST_FILTER_STATUSES).__name__!r}"
    )
    assert RUN_LIST_FILTER_STATUSES == case["expected_value"], (
        f"A3: exact 3-element membership pinned. Got {RUN_LIST_FILTER_STATUSES!r}"
    )


@pytest.mark.parametrize("case", RUN_HAS_STARTED_BASELINE_CASES, ids=lambda c: c["case_id"])
def test_run_has_started_baseline_matrix(case: dict[str, Any]) -> None:
    actual = _invoke_run_has_started(case)
    assert actual == case["expected"], case["msg"]


@pytest.mark.parametrize("case", STATUS_LADDER_CASES, ids=lambda c: c["case_id"])
def test_build_run_summary_status_ladder_matrix(case: dict[str, Any]) -> None:
    summary = _invoke_summary(case)
    assert_matrix_case(
        case["case_id"],
        expected=case["expected"],
        actual=summary,
        keys=tuple(case["expected"].keys()),
    )


@pytest.mark.parametrize("case", RUN_CREATED_EXTRACTION_CASES, ids=lambda c: c["case_id"])
def test_build_run_summary_run_created_extraction_matrix(case: dict[str, Any]) -> None:
    summary = _invoke_summary(case)
    if "expected" in case:
        assert_matrix_case(
            case["case_id"],
            expected=case["expected"],
            actual=summary,
            keys=tuple(case["expected"].keys()),
        )
    validate = case.get("validate")
    if validate is not None:
        validate(case, summary)


@pytest.mark.parametrize("case", FINDINGS_COUNT_CASES, ids=lambda c: c["case_id"])
def test_build_run_summary_findings_count_matrix(case: dict[str, Any]) -> None:
    summary = _invoke_summary(case)
    assert summary[case["expected_key"]] == case["expected"], case["case_id"]


@pytest.mark.parametrize("case", ESCALATION_FLAG_CASES, ids=lambda c: c["case_id"])
def test_build_run_summary_escalation_flag_matrix(case: dict[str, Any]) -> None:
    summary = _invoke_summary(case)
    assert summary[case["expected_key"]] == case["expected"], case["case_id"]


@pytest.mark.parametrize("case", EVENT_COUNT_LATEST_CASES, ids=lambda c: c["case_id"])
def test_build_run_summary_event_count_latest_matrix(case: dict[str, Any]) -> None:
    rows = _rows_for(case)
    summary = build_run_summary(rows)
    assert summary["event_count"] == len(rows), case["case_id"]
    assert summary["latest_event_type"] == case["expected_latest"], case["case_id"]


@pytest.mark.parametrize("case", RUN_HAS_STARTED_POSITION_CASES, ids=lambda c: c["case_id"])
def test_run_has_started_position_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=_invoke_run_has_started)


@pytest.mark.parametrize("case", RUN_HAS_STARTED_MALFORMED_CASES, ids=lambda c: c["case_id"])
def test_run_has_started_malformed_matrix(case: dict[str, Any]) -> None:
    if case["mode"] == "raise":
        run_exception_matrix(
            (case,),
            invoke=lambda c: run_has_started(c["rows_builder"]()),
        )
    else:
        run_value_matrix((case,), invoke=_invoke_run_has_started)
