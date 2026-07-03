from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from agent_core.critique_stages import (
    FRONTEND_WRITER_CRITIQUE_STAGE,
    IMPLEMENTATION_CRITIQUE_STAGE,
    PLANNER_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
)
from extensions.extension_runtime import UniversalCritiqueRouter
from orchestrator.llm.common import (
    MODULE_INTEGRATOR_CRITIQUE_STAGE,
    SELF_REFINEMENT_CRITIQUE_STAGE,
)
from orchestrator.llm.post_verify_role_critique import bind_post_verify_role_critique
from orchestrator.registry import RoleRegistry
from store.protocol import EventStore

EmitStubPanel = Callable[
    [EventStore, RoleRegistry, UniversalCritiqueRouter],
    None,
]
ExecuteRoleCritiqueLlm = Callable[..., bool]


@dataclass(frozen=True)
class _RoleBindingSpec:
    name: str
    producer_tax_key: str
    stage_name: str
    evidence_tag: str
    review_label: str | None = None
    min_pairing_count: int = 2
    max_critics: int | None = None
    stub_only: bool = False


_ROLE_SPECS: tuple[_RoleBindingSpec, ...] = (
    _RoleBindingSpec(
        "implementation",
        "backend_writer",
        IMPLEMENTATION_CRITIQUE_STAGE,
        "implementation",
    ),
    _RoleBindingSpec("planner", "planner", PLANNER_CRITIQUE_STAGE, "planner"),
    _RoleBindingSpec("test_writer", "test_writer", TEST_WRITER_CRITIQUE_STAGE, "test_writer"),
    _RoleBindingSpec(
        "frontend_writer",
        "frontend_writer",
        FRONTEND_WRITER_CRITIQUE_STAGE,
        "frontend_writer",
        "frontend writer",
    ),
    _RoleBindingSpec(
        "module_integrator",
        "module_integrator",
        MODULE_INTEGRATOR_CRITIQUE_STAGE,
        "module_integrator",
        "module integrator",
    ),
    _RoleBindingSpec(
        "self_refinement",
        "planner",
        SELF_REFINEMENT_CRITIQUE_STAGE,
        "self_refinement",
        min_pairing_count=1,
        max_critics=2,
        stub_only=True,
    ),
)


def _bind_all() -> dict[str, EmitStubPanel | ExecuteRoleCritiqueLlm]:
    bound: dict[str, EmitStubPanel | ExecuteRoleCritiqueLlm] = {}
    for spec in _ROLE_SPECS:
        emit, execute = bind_post_verify_role_critique(
            name=spec.name,
            producer_tax_key=spec.producer_tax_key,
            stage_name=spec.stage_name,
            evidence_tag=spec.evidence_tag,
            review_label=spec.review_label,
            min_pairing_count=spec.min_pairing_count,
            max_critics=spec.max_critics,
            bind_execute_llm=not spec.stub_only,
        )
        bound[f"emit_stub_{spec.name}_critique_panel"] = emit  # type: ignore[assignment]
        if execute is not None:
            bound[f"execute_{spec.name}_critique_llm"] = execute  # type: ignore[assignment]
    return bound


_bound = _bind_all()

emit_stub_implementation_critique_panel: EmitStubPanel = _bound[  # type: ignore[assignment]
    "emit_stub_implementation_critique_panel"
]
emit_stub_planner_critique_panel: EmitStubPanel = _bound["emit_stub_planner_critique_panel"]  # type: ignore[assignment]
execute_planner_critique_llm: ExecuteRoleCritiqueLlm = _bound["execute_planner_critique_llm"]  # type: ignore[assignment]
emit_stub_test_writer_critique_panel: EmitStubPanel = _bound["emit_stub_test_writer_critique_panel"]  # type: ignore[assignment]
execute_test_writer_critique_llm: ExecuteRoleCritiqueLlm = _bound[
    "execute_test_writer_critique_llm"
]  # type: ignore[assignment]
emit_stub_frontend_writer_critique_panel: EmitStubPanel = _bound[  # type: ignore[assignment]
    "emit_stub_frontend_writer_critique_panel"
]
execute_frontend_writer_critique_llm: ExecuteRoleCritiqueLlm = _bound[  # type: ignore[assignment]
    "execute_frontend_writer_critique_llm"
]
emit_stub_module_integrator_critique_panel: EmitStubPanel = _bound[  # type: ignore[assignment]
    "emit_stub_module_integrator_critique_panel"
]
emit_stub_self_refinement_critique_panel: EmitStubPanel = _bound[  # type: ignore[assignment]
    "emit_stub_self_refinement_critique_panel"
]
execute_module_integrator_critique_llm: ExecuteRoleCritiqueLlm = _bound[  # type: ignore[assignment]
    "execute_module_integrator_critique_llm"
]

__all__ = [
    "emit_stub_frontend_writer_critique_panel",
    "emit_stub_implementation_critique_panel",
    "emit_stub_module_integrator_critique_panel",
    "emit_stub_planner_critique_panel",
    "emit_stub_self_refinement_critique_panel",
    "emit_stub_test_writer_critique_panel",
    "execute_frontend_writer_critique_llm",
    "execute_module_integrator_critique_llm",
    "execute_planner_critique_llm",
    "execute_test_writer_critique_llm",
]
