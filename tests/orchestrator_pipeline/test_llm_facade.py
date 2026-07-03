from __future__ import annotations

import orchestrator.llm as llm


def test_llm_package_exports_plan_and_critique_symbols() -> None:
    for name in (
        "execute_plan_stage_llm",
        "emit_stub_plan_stage",
        "execute_implementation_critique_llm",
        "IMPLEMENTATION_CRITIQUE_STAGE",
    ):
        assert hasattr(llm, name), name


def test_llm_submodules_exist() -> None:
    from orchestrator.llm import implementation_critique, plan_stage

    assert hasattr(plan_stage, "execute_plan_stage_llm")
    assert hasattr(implementation_critique, "execute_implementation_critique_llm")
