from __future__ import annotations

from uuid import UUID

from nimbusware_extensions.phase2 import UniversalCritiqueRouter
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.workflow_universal_critique import EffectiveUniversalCritique

CANONICAL_PRODUCERS = ("planner", "backend_writer", "test_writer")
CANONICAL_CRITICS = ("product_reference_critic", "domain_critic")
CANONICAL_DEFAULT_CRITICS = CANONICAL_CRITICS


def deterministic_uuid(n: int) -> UUID:
    """Deterministic UUID for test fixtures (no real role IDs needed)."""
    return UUID(int=n)


def canonical_role_registry() -> RoleRegistry:
    """Registry matching the real ``configs/roles.yaml`` keys."""
    return RoleRegistry.from_mapping(
        {
            "planner": deterministic_uuid(1),
            "backend_writer": deterministic_uuid(2),
            "test_writer": deterministic_uuid(3),
            "product_reference_critic": deterministic_uuid(4),
            "domain_critic": deterministic_uuid(5),
        }
    )


def canonical_critique_router() -> UniversalCritiqueRouter:
    """Router matching the real ``configs/personas/critique_pairings.yaml``."""
    return UniversalCritiqueRouter(
        {
            "planner": list(CANONICAL_CRITICS),
            "backend_writer": list(CANONICAL_CRITICS),
            "test_writer": list(CANONICAL_CRITICS),
        }
    )


def all_false_effective_critique() -> EffectiveUniversalCritique:
    return EffectiveUniversalCritique(
        impl_llm=False,
        impl_stub=False,
        impl_stage_failed_on_gate_fail=False,
        impl_emit_finding_on_gate_fail=False,
        impl_hard_block_on_gate_fail=False,
        tw_enabled=False,
        tw_llm=False,
        tw_stub=False,
        tw_stage_failed_on_gate_fail=False,
        tw_emit_finding_on_gate_fail=False,
        tw_hard_block_on_gate_fail=False,
        pll_enabled=False,
        pll_llm=False,
        pll_stub=False,
        pll_stage_failed_on_gate_fail=False,
        pll_emit_finding_on_gate_fail=False,
        pll_hard_block_on_gate_fail=False,
    )
