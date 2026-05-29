"""Phase 2–4 extension points ."""

from hermes_extensions.catalog import (
    BundleCatalog,
    assert_workflow_bundle_map_ids_resolve,
    bundle_faiss_index_ready,
    bundle_faiss_index_sync_state,
    search_bundles,
)
from hermes_extensions.escalation import EscalationPolicy
from hermes_extensions.personas import PersonaShelf
from hermes_extensions.phase2 import (
    AgentEvaluator,
    ModuleIntegrator,
    SecurityScanner,
    SecurityScannerStub,
    UniversalCritiqueRouter,
)
from hermes_extensions.self_refinement import SelfRefinementPolicy, load_self_refinement_policy

__all__ = [
    "AgentEvaluator",
    "BundleCatalog",
    "assert_workflow_bundle_map_ids_resolve",
    "bundle_faiss_index_ready",
    "bundle_faiss_index_sync_state",
    "search_bundles",
    "EscalationPolicy",
    "ModuleIntegrator",
    "PersonaShelf",
    "SecurityScanner",
    "SecurityScannerStub",
    "SelfRefinementPolicy",
    "UniversalCritiqueRouter",
    "load_self_refinement_policy",
]
