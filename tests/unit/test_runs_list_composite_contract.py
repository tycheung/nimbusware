from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.routes.runs import _decode_run_list_cursor, _parse_query_datetime
from unit.composite_contracts.matrix_runner import run_exception_matrix, run_value_matrix
from unit.composite_contracts.runs_list_matrix import (
    CATCH_TUPLE_PREFLIGHT,
    DECODE_CURSOR_PART_A_EXCEPTION_CASES,
    DECODE_CURSOR_PART_B_EXCEPTION_CASES,
    DECODE_CURSOR_PART_C_EXCEPTION_CASES,
    PARSE_DATETIME_EXCEPTION_CASES,
    PARSE_DATETIME_VALUE_CASES,
    ROUTE_EMPTY_CURSOR_200_CASES,
    ROUTE_INVALID_CURSOR_422_CASES,
)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def _invoke_parse_datetime(case: dict[str, Any]) -> Any:
    return _parse_query_datetime(case["field"], case["raw"])


def _invoke_decode_cursor(case: dict[str, Any]) -> Any:
    return _decode_run_list_cursor(case["cursor"])


@pytest.mark.parametrize("case", CATCH_TUPLE_PREFLIGHT, ids=lambda c: c["case_id"])
def test_catch_tuple_exception_class_inheritance_preflight(case: dict[str, Any]) -> None:
    is_sub = issubclass(case["subclass"], case["base"])
    assert is_sub == case["expect_subclass"], (
        f"preflight: {case['subclass'].__name__} issubclass "
        f"{case['base'].__name__} expected {case['expect_subclass']}, got {is_sub}"
    )


@pytest.mark.parametrize("case", PARSE_DATETIME_VALUE_CASES, ids=lambda c: c["case_id"])
def test_parse_query_datetime_value_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=_invoke_parse_datetime)


@pytest.mark.parametrize("case", PARSE_DATETIME_EXCEPTION_CASES, ids=lambda c: c["case_id"])
def test_parse_query_datetime_exception_matrix(case: dict[str, Any]) -> None:
    run_exception_matrix((case,), invoke=_invoke_parse_datetime)


def test_d2_created_after_and_before_messages_differ() -> None:
    with pytest.raises(ValueError) as before_exc:
        _parse_query_datetime("created_before", "not-a-date")
    with pytest.raises(ValueError) as after_exc:
        _parse_query_datetime("created_after", "not-a-date")
    assert str(before_exc.value) != str(after_exc.value)


@pytest.mark.parametrize("case", DECODE_CURSOR_PART_A_EXCEPTION_CASES, ids=lambda c: c["case_id"])
def test_decode_cursor_part_a_exception_matrix(case: dict[str, Any]) -> None:
    run_exception_matrix((case,), invoke=_invoke_decode_cursor)


@pytest.mark.parametrize("case", DECODE_CURSOR_PART_B_EXCEPTION_CASES, ids=lambda c: c["case_id"])
def test_decode_cursor_part_b_exception_matrix(case: dict[str, Any]) -> None:
    run_exception_matrix((case,), invoke=_invoke_decode_cursor)


@pytest.mark.parametrize("case", DECODE_CURSOR_PART_C_EXCEPTION_CASES, ids=lambda c: c["case_id"])
def test_decode_cursor_part_c_exception_matrix(case: dict[str, Any]) -> None:
    run_exception_matrix((case,), invoke=_invoke_decode_cursor)


@pytest.mark.parametrize("case", ROUTE_INVALID_CURSOR_422_CASES, ids=lambda c: c["case_id"])
def test_route_invalid_cursor_422_matrix(client: TestClient, case: dict[str, Any]) -> None:
    response = client.get("/v1/runs", params={"cursor": case["cursor"], "limit": 5})
    assert response.status_code == case["expected_status"], (
        f"{case['case_id']}: expected {case['expected_status']}, "
        f"got {response.status_code} body={response.text!r}"
    )
    body = response.json()
    assert body.get("code") == case["expected_code"], (
        f"{case['case_id']}: code expected {case['expected_code']!r}, got {body!r}"
    )
    if "expected_message" in case:
        assert body.get("message") == case["expected_message"]
    if case.get("assert_details_reason"):
        details = body.get("details") or {}
        assert isinstance(details, dict) and "reason" in details
        reason = details["reason"]
        assert isinstance(reason, str) and reason.strip() != ""


@pytest.mark.parametrize("case", ROUTE_EMPTY_CURSOR_200_CASES, ids=lambda c: c["case_id"])
def test_route_empty_cursor_200_matrix(client: TestClient, case: dict[str, Any]) -> None:
    response = client.get("/v1/runs", params=case["params"])
    assert response.status_code == 200, (
        f"{case['case_id']}: expected 200, got {response.status_code} body={response.text!r}"
    )
