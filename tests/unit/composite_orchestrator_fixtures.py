from __future__ import annotations

from uuid import UUID

from nimbusware_extensions.extension_runtime import UniversalCritiqueRouter
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.workflow_universal_critique import EffectiveUniversalCritique

from unit.composite_contracts.optional_critique_emit_matrix import make_effective_universal_critique

CANONICAL_PRODUCERS = ("planner", "backend_writer", "test_writer")
CANONICAL_CRITICS = ("product_reference_critic", "domain_critic")
CANONICAL_DEFAULT_CRITICS = CANONICAL_CRITICS


def deterministic_uuid(n: int) -> UUID:
    return UUID(int=n)


def canonical_role_registry() -> RoleRegistry:
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
    return UniversalCritiqueRouter(
        {
            "planner": list(CANONICAL_CRITICS),
            "backend_writer": list(CANONICAL_CRITICS),
            "test_writer": list(CANONICAL_CRITICS),
        }
    )


def all_false_effective_critique() -> EffectiveUniversalCritique:
    return make_effective_universal_critique()
