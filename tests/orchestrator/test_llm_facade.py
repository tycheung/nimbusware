from __future__ import annotations

import nimbusware_orchestrator.llm_plan as llm_plan


def test_llm_plan_shim_re_exports_package() -> None:
    for name in (
        "execute_plan_stage_llm",
        "emit_stub_plan_stage",
        "execute_implementation_critique_llm",
        "IMPLEMENTATION_CRITIQUE_STAGE",
    ):
        assert hasattr(llm_plan, name), name


def test_llm_submodules_exist() -> None:
    from nimbusware_orchestrator.llm import implementation_critique, plan_stage

    assert hasattr(plan_stage, "execute_plan_stage_llm")
    assert hasattr(implementation_critique, "execute_implementation_critique_llm")
