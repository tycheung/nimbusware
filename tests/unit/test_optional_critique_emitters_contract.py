from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from nimbusware_orchestrator.pipeline import make_dev_orchestrator
from unit.composite_contracts.optional_critique_emit_matrix import (
    MATRIX_6_AXIS,
    OPTIONAL_CRITIQUE_EMITTER_SPECS,
    OptionalCritiqueEmitterSpec,
    append_model_selected_primary,
    make_propagation_eff,
    run_optional_critique_matrix_case,
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


_PROPAGATION_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "base_url_default",
        "base_cfg": {},
        "expect_base_url": "http://localhost:11434",
        "expect_timeout": 120.0,
        "verifier_exit_code": 0,
        "log_snippet": "ok",
        "model_id": "llama3.1:8b",
    },
    {
        "case_id": "base_url_override",
        "base_cfg": {"runtime": {"base_url": "http://example:9000"}},
        "expect_base_url": "http://example:9000",
        "expect_timeout": 120.0,
        "verifier_exit_code": 0,
        "log_snippet": "ok",
        "model_id": "llama3.1:8b",
    },
    {
        "case_id": "timeout_default",
        "base_cfg": {},
        "expect_base_url": "http://localhost:11434",
        "expect_timeout": 120.0,
        "verifier_exit_code": 0,
        "log_snippet": "ok",
        "model_id": "llama3.1:8b",
        "assert_timeout_type": True,
    },
    {
        "case_id": "timeout_override",
        "base_cfg": {"runtime": {"request_timeout_seconds": 30}},
        "expect_base_url": "http://localhost:11434",
        "expect_timeout": 30.0,
        "verifier_exit_code": 0,
        "log_snippet": "ok",
        "model_id": "llama3.1:8b",
        "assert_timeout_type": True,
    },
    {
        "case_id": "kwargs_propagation",
        "base_cfg": None,
        "expect_base_url": None,
        "expect_timeout": None,
        "verifier_exit_code": 42,
        "log_snippet": "LOG_X",
        "model_id": "custom-model:13b",
    },
)


@pytest.mark.parametrize("spec", OPTIONAL_CRITIQUE_EMITTER_SPECS, ids=lambda s: s.prefix)
@pytest.mark.parametrize("case", _PROPAGATION_CASES, ids=lambda c: c["case_id"])
def test_optional_critique_argument_propagation(
    spec: OptionalCritiqueEmitterSpec,
    case: dict[str, Any],
) -> None:
    eff = make_propagation_eff(spec)
    with (
        patch(spec.llm_patch) as m_llm,
        patch(spec.stub_patch),
    ):
        m_llm.return_value = True
        orch, mem = make_dev_orchestrator()
        rid = orch.create_run("default")
        append_model_selected_primary(mem, rid, model_id=case["model_id"])
        emit = getattr(orch, spec.emit_method)
        if case["base_cfg"] is None:
            emit(
                rid,
                verifier_exit_code=case["verifier_exit_code"],
                log_snippet=case["log_snippet"],
                eff=eff,
            )
        else:
            with patch.object(orch, "_base_cfg", return_value=case["base_cfg"]):
                emit(
                    rid,
                    verifier_exit_code=case["verifier_exit_code"],
                    log_snippet=case["log_snippet"],
                    eff=eff,
                )
        kw = m_llm.call_args.kwargs
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
