from __future__ import annotations

from typing import Any

import pytest

from unit.composite_contracts.optional_critique_emit_matrix import (
    MATRIX_6_AXIS,
    OPTIONAL_CRITIQUE_EMITTER_SPECS,
    PROPAGATION_CASES,
    OptionalCritiqueEmitterSpec,
    run_optional_critique_matrix_case,
    run_optional_critique_propagation_case,
)


@pytest.mark.parametrize("spec", OPTIONAL_CRITIQUE_EMITTER_SPECS, ids=lambda s: s.prefix)
@pytest.mark.parametrize("case", MATRIX_6_AXIS, ids=lambda c: c["case_id"])
def test_optional_critique_emit_path_matrix(
    spec: OptionalCritiqueEmitterSpec,
    case: dict[str, Any],
) -> None:
    llm_count, stub_count = run_optional_critique_matrix_case(spec, case)
    assert llm_count == case["expected_llm"], (
        f"{spec.prefix}/{case['case_id']}: expected llm={case['expected_llm']}, got {llm_count}"
    )
    assert stub_count == case["expected_stub"], (
        f"{spec.prefix}/{case['case_id']}: expected stub={case['expected_stub']}, got {stub_count}"
    )


@pytest.mark.parametrize("spec", OPTIONAL_CRITIQUE_EMITTER_SPECS, ids=lambda s: s.prefix)
@pytest.mark.parametrize("case", PROPAGATION_CASES, ids=lambda c: c["case_id"])
def test_optional_critique_argument_propagation(
    spec: OptionalCritiqueEmitterSpec,
    case: dict[str, Any],
) -> None:
    kw, rid = run_optional_critique_propagation_case(spec, case)
    if case["case_id"] == "kwargs_propagation":
        assert kw["run_id"] == rid
        assert kw["model_id"] == case["model_id"]
        assert kw["verifier_exit_code"] == case["verifier_exit_code"]
        assert kw["log_snippet"] == case["log_snippet"]
        return
    assert kw["base_url"] == case["expect_base_url"]
    timeout = kw["timeout_seconds"]
    assert timeout == case["expect_timeout"]
    if case.get("assert_timeout_type"):
        assert isinstance(timeout, float)
