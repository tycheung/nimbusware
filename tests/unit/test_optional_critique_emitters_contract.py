from __future__ import annotations

from typing import Any

import pytest

from unit.composite_contracts.matrix_runner import run_patch_matrix
from unit.composite_contracts.optional_critique_emit_matrix import (
    MATRIX_6_AXIS,
    OPTIONAL_CRITIQUE_EMITTER_SPECS,
    PROPAGATION_CASES,
    OptionalCritiqueEmitterSpec,
    run_optional_critique_matrix_case,
    run_optional_critique_propagation_case,
)


@pytest.mark.parametrize("spec", OPTIONAL_CRITIQUE_EMITTER_SPECS, ids=lambda s: s.prefix)
def test_optional_critique_emit_path_matrix(spec: OptionalCritiqueEmitterSpec) -> None:
    run_patch_matrix(
        MATRIX_6_AXIS,
        invoke=lambda case: run_optional_critique_matrix_case(spec, case),
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
