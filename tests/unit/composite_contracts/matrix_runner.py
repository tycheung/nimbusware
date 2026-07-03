from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


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
