from __future__ import annotations

from typing import Any

import pytest

from unit.composite_contracts.matrix_runner import run_value_matrix
from unit.composite_contracts.timeline_summary_quintet_matrix import (
    AGENT_EVALUATOR_PERSONA_CASES,
    INTEGRATOR_GATE_DIRECT_CASES,
    INTEGRATOR_GATE_METADATA_SKIP_CASES,
    SECURITY_SCAN_GUARD_CASES,
    SELF_REFINEMENT_AND_ESCALATED_CASES,
    invoke_timeline_summary_case,
)


@pytest.mark.parametrize("case", INTEGRATOR_GATE_DIRECT_CASES, ids=lambda c: c["case_id"])
def test_integrator_gate_timeline_summary_direct_contract_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=invoke_timeline_summary_case)


@pytest.mark.parametrize(
    "case",
    INTEGRATOR_GATE_METADATA_SKIP_CASES,
    ids=lambda c: c["case_id"],
)
def test_integrator_gate_metadata_skip_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=invoke_timeline_summary_case)


@pytest.mark.parametrize("case", AGENT_EVALUATOR_PERSONA_CASES, ids=lambda c: c["case_id"])
def test_agent_evaluator_timeline_summary_persona_split_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=invoke_timeline_summary_case)


@pytest.mark.parametrize(
    "case",
    SELF_REFINEMENT_AND_ESCALATED_CASES,
    ids=lambda c: c["case_id"],
)
def test_self_refinement_and_run_escalated_summary_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=invoke_timeline_summary_case)


@pytest.mark.parametrize("case", SECURITY_SCAN_GUARD_CASES, ids=lambda c: c["case_id"])
def test_security_scan_summary_and_guard_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=invoke_timeline_summary_case)
