from __future__ import annotations

from typing import Any

import pytest

from unit.composite_contracts.critique_gate_fail_matrix import (
    EFF_NONE_FALLBACK_PARAM_CASES,
    ITERATION_ORDER_CASES,
    ROWS_REFRESH_CASES,
    STRICTNESS_CONTEXT_CASES,
    run_eff_none_fallback_param,
    run_eff_none_fallback_parity,
    run_eff_none_fallback_resolver,
    run_iteration_order_case,
    run_rows_refresh_case,
    run_strictness_context_case,
)
from unit.composite_contracts.matrix_runner import run_value_matrix


@pytest.mark.parametrize("case", EFF_NONE_FALLBACK_PARAM_CASES, ids=lambda c: c["case_id"])
def test_critique_gate_fail_findings_eff_none_fallback_param_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=run_eff_none_fallback_param)


def test_critique_gate_fail_findings_eff_none_fallback_parity_matrix() -> None:
    run_eff_none_fallback_parity()


def test_critique_gate_fail_findings_eff_none_fallback_resolver_matrix() -> None:
    run_eff_none_fallback_resolver()


@pytest.mark.parametrize("case", ITERATION_ORDER_CASES, ids=lambda c: c["case_id"])
def test_critique_gate_fail_findings_iteration_order_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=run_iteration_order_case)


@pytest.mark.parametrize("case", STRICTNESS_CONTEXT_CASES, ids=lambda c: c["case_id"])
def test_critique_gate_fail_findings_strictness_context_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=run_strictness_context_case)


@pytest.mark.parametrize("case", ROWS_REFRESH_CASES, ids=lambda c: c["case_id"])
def test_critique_gate_fail_findings_rows_refresh_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=run_rows_refresh_case)
