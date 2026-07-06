from __future__ import annotations

from typing import Any

import pytest

from api.routes.runs import _runs_list_query_string
from unit.composite_contracts.matrix_runner import run_value_matrix
from unit.composite_contracts.runs_list_wire_format_matrix import (
    LINK_HEADER_NAVIGATION_CASE,
    LINK_HEADER_STRUCTURAL_CASE,
    QUERY_STRING_BASE_OFFSET_CASES,
    QUERY_STRING_OPTIONAL_APPEND_CASES,
)


def _invoke_query_string(case: dict[str, Any]) -> str:
    return _runs_list_query_string(**case["kwargs"])


def _invoke_link_header_validate(case: dict[str, Any]) -> None:
    return None


def _run_query_string_matrix(case: dict[str, Any]) -> None:
    actual = _invoke_query_string(case)
    if "expected" in case:
        assert actual == case["expected"], (
            f"{case['case_id']}: expected {case['expected']!r}, got {actual!r}"
        )
    if "expected_contains" in case:
        assert case["expected_contains"] in actual, (
            f"{case['case_id']}: expected substring {case['expected_contains']!r} in {actual!r}"
        )
    if "forbidden_contains" in case:
        assert case["forbidden_contains"] not in actual, (
            f"{case['case_id']}: forbidden substring {case['forbidden_contains']!r} in {actual!r}"
        )
    validate = case.get("validate")
    if validate is not None:
        validate(case, actual)


def test_link_header_trio_structural_shape_matrix() -> None:
    run_value_matrix(
        (LINK_HEADER_STRUCTURAL_CASE,),
        invoke=_invoke_link_header_validate,
    )


def test_link_header_trio_navigation_triangle_and_determinism_matrix() -> None:
    run_value_matrix(
        (LINK_HEADER_NAVIGATION_CASE,),
        invoke=_invoke_link_header_validate,
    )


@pytest.mark.parametrize("case", QUERY_STRING_BASE_OFFSET_CASES, ids=lambda c: c["case_id"])
def test_runs_list_query_string_base_and_offset_matrix(case: dict[str, Any]) -> None:
    _run_query_string_matrix(case)


@pytest.mark.parametrize("case", QUERY_STRING_OPTIONAL_APPEND_CASES, ids=lambda c: c["case_id"])
def test_runs_list_query_string_optional_appends_and_rename_matrix(case: dict[str, Any]) -> None:
    _run_query_string_matrix(case)
