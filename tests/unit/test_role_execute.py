from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from hermes_orchestrator.registry import RoleRegistry
from hermes_orchestrator.role_execute import dispatch_role_execute, resolve_taxonomy_key


class _FakeOrch:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute_plan_stage(self, run_id: UUID) -> None:
        self.calls.append(f"plan:{run_id}")

    def execute_writer_verifier_pass(self, run_id: UUID, *, workspace: Path | None = None) -> None:
        self.calls.append(f"verify:{run_id}")

    def _maybe_emit_agent_evaluator_stage(self, run_id: UUID) -> None:
        self.calls.append(f"ae:{run_id}")

    def _emit_bundle_integrator_gate(self, run_id: UUID) -> None:
        self.calls.append(f"integrator:{run_id}")

    def _maybe_emit_integration_adapter_writer_stage(self, run_id: UUID) -> None:
        self.calls.append(f"iaw:{run_id}")

    def _maybe_emit_research_stages(self, run_id: UUID) -> None:
        self.calls.append(f"research:{run_id}")

    def _maybe_emit_stitch_stages(self, run_id: UUID) -> None:
        self.calls.append(f"stitch:{run_id}")


def _registry() -> RoleRegistry:
    return RoleRegistry.from_yaml(Path("configs/roles.yaml"))


def test_resolve_taxonomy_key_by_uuid() -> None:
    reg = _registry()
    key = resolve_taxonomy_key(reg, "11111111-1111-4111-8111-111111111101")
    assert key == "planner"


def test_resolve_taxonomy_key_by_name() -> None:
    reg = _registry()
    assert resolve_taxonomy_key(reg, "planner") == "planner"


def test_dispatch_planner() -> None:
    orch = _FakeOrch()
    run_id = uuid4()
    out = dispatch_role_execute(orch, run_id, "planner")
    assert out["status"] == "executed"
    assert orch.calls == [f"plan:{run_id}"]


def test_dispatch_unsupported_critic() -> None:
    orch = _FakeOrch()
    with pytest.raises(ValueError, match="not supported"):
        dispatch_role_execute(orch, uuid4(), "security_critic")
