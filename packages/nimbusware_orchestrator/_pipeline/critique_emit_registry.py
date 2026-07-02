from __future__ import annotations

from typing import Any

from nimbusware_orchestrator._pipeline.role_critique_emit import RoleCritiqueEmitSpec


def test_writer_optional_spec() -> RoleCritiqueEmitSpec:
    from nimbusware_orchestrator._pipeline import critique_gates_optional_emit as surface

    return RoleCritiqueEmitSpec(
        enabled=lambda e: e.tw_enabled,
        llm=lambda e: e.tw_llm,
        stub=lambda e: e.tw_stub,
        execute_llm=surface.execute_test_writer_critique_llm,
        emit_stub=surface.emit_stub_test_writer_critique_panel,
    )


def planner_optional_spec() -> RoleCritiqueEmitSpec:
    from nimbusware_orchestrator._pipeline import critique_gates_optional_emit as surface

    return RoleCritiqueEmitSpec(
        enabled=lambda e: e.pll_enabled,
        llm=lambda e: e.pll_llm,
        stub=lambda e: e.pll_stub,
        execute_llm=surface.execute_planner_critique_llm,
        emit_stub=surface.emit_stub_planner_critique_panel,
    )


def module_integrator_optional_spec() -> RoleCritiqueEmitSpec:
    from nimbusware_orchestrator._pipeline import critique_gates_optional_emit as surface

    return RoleCritiqueEmitSpec(
        enabled=lambda e: e.mi_enabled,
        llm=lambda e: e.mi_llm,
        stub=lambda e: e.mi_stub,
        execute_llm=surface.execute_module_integrator_critique_llm,
        emit_stub=surface.emit_stub_module_integrator_critique_panel,
    )


def frontend_writer_optional_spec(*, pre_emit: Any) -> RoleCritiqueEmitSpec:
    from nimbusware_orchestrator._pipeline import critique_gates_optional_emit as surface

    return RoleCritiqueEmitSpec(
        enabled=lambda e: e.fw_enabled,
        llm=lambda e: e.fw_llm,
        stub=lambda e: e.fw_stub,
        execute_llm=surface.execute_frontend_writer_critique_llm,
        emit_stub=surface.emit_stub_frontend_writer_critique_panel,
        pre_emit=pre_emit,
    )


def security_critique_scan_spec():
    from nimbusware_orchestrator._pipeline._helpers import (
        ScanCritiqueEmitSpec,
        emit_stub_security_critique_panel,
        execute_security_critique_llm,
        parse_security_critique_workflow_block,
        run_security_scan_summary,
        security_critique_effective,
        security_critique_llm_branch_effective,
    )

    return ScanCritiqueEmitSpec(
        parse_block=parse_security_critique_workflow_block,
        effective=security_critique_effective,
        llm_effective=security_critique_llm_branch_effective,
        stage_id="implementation.security_critique",
        run_scan=run_security_scan_summary,
        execute_llm=execute_security_critique_llm,
        emit_stub=emit_stub_security_critique_panel,
    )
