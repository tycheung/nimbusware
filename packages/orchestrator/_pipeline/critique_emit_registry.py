from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from orchestrator._pipeline.role_critique_emit import RoleCritiqueEmitSpec


@dataclass(frozen=True)
class RoleCritiqueEmitKeys:
    kind: Literal["role"]
    enabled_key: str
    llm_key: str
    stub_key: str
    execute_llm_module: str
    emit_stub_module: str


@dataclass(frozen=True)
class ScanCritiqueEmitKeys:
    kind: Literal["scan"]
    stage_id: str


CRITIQUE_EMIT_SPECS: dict[str, RoleCritiqueEmitKeys | ScanCritiqueEmitKeys] = {
    "test_writer": RoleCritiqueEmitKeys(
        kind="role",
        enabled_key="tw_enabled",
        llm_key="tw_llm",
        stub_key="tw_stub",
        execute_llm_module=(
            "orchestrator._pipeline.critique_gates_optional_emit.execute_test_writer_critique_llm"
        ),
        emit_stub_module=(
            "orchestrator._pipeline.critique_gates_optional_emit.emit_stub_test_writer_critique_panel"
        ),
    ),
    "planner": RoleCritiqueEmitKeys(
        kind="role",
        enabled_key="pll_enabled",
        llm_key="pll_llm",
        stub_key="pll_stub",
        execute_llm_module=(
            "orchestrator._pipeline.critique_gates_optional_emit.execute_planner_critique_llm"
        ),
        emit_stub_module=(
            "orchestrator._pipeline.critique_gates_optional_emit.emit_stub_planner_critique_panel"
        ),
    ),
    "module_integrator": RoleCritiqueEmitKeys(
        kind="role",
        enabled_key="mi_enabled",
        llm_key="mi_llm",
        stub_key="mi_stub",
        execute_llm_module=(
            "orchestrator._pipeline.critique_gates_optional_emit.execute_module_integrator_critique_llm"
        ),
        emit_stub_module=(
            "orchestrator._pipeline.critique_gates_optional_emit.emit_stub_module_integrator_critique_panel"
        ),
    ),
    "frontend_writer": RoleCritiqueEmitKeys(
        kind="role",
        enabled_key="fw_enabled",
        llm_key="fw_llm",
        stub_key="fw_stub",
        execute_llm_module=(
            "orchestrator._pipeline.critique_gates_optional_emit.execute_frontend_writer_critique_llm"
        ),
        emit_stub_module=(
            "orchestrator._pipeline.critique_gates_optional_emit.emit_stub_frontend_writer_critique_panel"
        ),
    ),
    "security_scan": ScanCritiqueEmitKeys(
        kind="scan",
        stage_id="implementation.security_critique",
    ),
}


def _role_critique_emit_spec(name: str, *, pre_emit: Any = None) -> RoleCritiqueEmitSpec:
    keys = CRITIQUE_EMIT_SPECS[name]
    if keys.kind != "role":
        msg = f"{name!r} is not a role critique emit spec"
        raise TypeError(msg)
    from orchestrator._pipeline import critique_gates_optional_emit as surface

    return RoleCritiqueEmitSpec(
        enabled=lambda e, k=keys.enabled_key: getattr(e, k),
        llm=lambda e, k=keys.llm_key: getattr(e, k),
        stub=lambda e, k=keys.stub_key: getattr(e, k),
        execute_llm=getattr(surface, keys.execute_llm_module.rsplit(".", 1)[-1]),
        emit_stub=getattr(surface, keys.emit_stub_module.rsplit(".", 1)[-1]),
        pre_emit=pre_emit,
    )


def test_writer_optional_spec() -> RoleCritiqueEmitSpec:
    return _role_critique_emit_spec("test_writer")


def planner_optional_spec() -> RoleCritiqueEmitSpec:
    return _role_critique_emit_spec("planner")


def module_integrator_optional_spec() -> RoleCritiqueEmitSpec:
    return _role_critique_emit_spec("module_integrator")


def frontend_writer_optional_spec(*, pre_emit: Any) -> RoleCritiqueEmitSpec:
    return _role_critique_emit_spec("frontend_writer", pre_emit=pre_emit)


def security_critique_scan_spec() -> Any:
    keys = CRITIQUE_EMIT_SPECS["security_scan"]
    if keys.kind != "scan":
        msg = "security_scan spec must be scan kind"
        raise TypeError(msg)
    from orchestrator._pipeline._helpers import (
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
        stage_id=keys.stage_id,
        run_scan=run_security_scan_summary,
        execute_llm=execute_security_critique_llm,
        emit_stub=emit_stub_security_critique_panel,
    )
