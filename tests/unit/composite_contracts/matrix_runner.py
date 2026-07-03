from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import pytest


def assert_matrix_case(
    case_id: str,
    *,
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
    keys: tuple[str, ...],
) -> None:
    for key in keys:
        assert actual.get(key) == expected.get(key), (
            f"{case_id}: {key} expected {expected.get(key)!r}, got {actual.get(key)!r}"
        )


def run_patch_matrix(
    cases: tuple[Mapping[str, Any], ...],
    *,
    case_id_key: str = "case_id",
    invoke: Callable[[Mapping[str, Any]], tuple[int, int]],
) -> None:
    for case in cases:
        case_id = str(case.get(case_id_key) or "?")
        llm_calls, stub_calls = invoke(case)
        assert llm_calls == case.get("expected_llm", 0), f"{case_id}: llm calls"
        assert stub_calls == case.get("expected_stub", 0), f"{case_id}: stub calls"


def run_exception_matrix(
    cases: tuple[Mapping[str, Any], ...],
    *,
    case_id_key: str = "case_id",
    invoke: Callable[[Mapping[str, Any]], Any],
) -> None:
    for case in cases:
        case_id = str(case.get(case_id_key) or "?")
        exc_type = case.get("exc_type", ValueError)
        with pytest.raises(exc_type) as exc_info:
            invoke(case)
        exc = exc_info.value
        msg_contains = case.get("msg_contains", ())
        if msg_contains:
            if case.get("msg_contains_any"):
                assert any(substr in str(exc) for substr in msg_contains), (
                    f"{case_id}: expected one of {msg_contains!r} in {str(exc)!r}"
                )
            else:
                for substr in msg_contains:
                    assert substr in str(exc), f"{case_id}: expected {substr!r} in {str(exc)!r}"
        if "msg_equals" in case:
            assert str(exc) == case["msg_equals"], (
                f"{case_id}: message expected {case['msg_equals']!r}, got {str(exc)!r}"
            )
        for substr in case.get("msg_not_contains", ()):
            assert substr not in str(exc), f"{case_id}: expected {substr!r} not in {str(exc)!r}"
        if "exc_args" in case:
            assert exc.args == case["exc_args"], (
                f"{case_id}: args expected {case['exc_args']!r}, got {exc.args!r}"
            )
        if "assert_not_isinstance" in case:
            bad_type = case["assert_not_isinstance"]
            assert not isinstance(exc, bad_type), f"{case_id}: must not be {bad_type.__name__}"
        if "assert_encoding" in case:
            assert getattr(exc, "encoding", None) == case["assert_encoding"], (
                f"{case_id}: encoding expected {case['assert_encoding']!r}, "
                f"got {getattr(exc, 'encoding', None)!r}"
            )
        validate = case.get("validate")
        if validate is not None:
            validate(case, exc)


def run_value_matrix(
    cases: tuple[Mapping[str, Any], ...],
    *,
    case_id_key: str = "case_id",
    invoke: Callable[[Mapping[str, Any]], Any],
) -> None:
    for case in cases:
        case_id = str(case.get(case_id_key) or "?")
        actual = invoke(case)
        if "expected" in case:
            assert actual == case["expected"], (
                f"{case_id}: expected {case['expected']!r}, got {actual!r}"
            )
        if case.get("assert_tz_utc"):
            assert actual is not None and actual.tzinfo is case.get("tzinfo"), (
                f"{case_id}: expected tzinfo {case.get('tzinfo')!r}, got "
                f"{getattr(actual, 'tzinfo', None)!r}"
            )
        if case.get("assert_midnight"):
            assert actual is not None
            assert (
                actual.hour == 0
                and actual.minute == 0
                and actual.second == 0
                and actual.microsecond == 0
            ), f"{case_id}: expected midnight time components"
        validate = case.get("validate")
        if validate is not None:
            validate(case, actual)
