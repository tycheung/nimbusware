"""YAML merge, Role Registry, preflight, and MVP orchestration (plan §5–§6.3A).

Avoid importing ``pipeline`` at package import time: ``pipeline`` depends on
``hermes_extensions``, while ``hermes_extensions`` (e.g. ``catalog``) imports
``hermes_orchestrator.merge`` — eager ``pipeline`` import would create a cycle.
``RunOrchestrator`` is exposed lazily via :pep:`562` ``__getattr__``.
"""

from __future__ import annotations

from typing import Any

from hermes_orchestrator.ingress import (
    assert_bundle_catalog_maps_resolve,
    assert_known_workflow,
    assert_persona_shelves_valid,
    assert_taxonomy_keys_resolve,
)
from hermes_orchestrator.merge import load_yaml, merge_policy_snapshot
from hermes_orchestrator.preflight import PreflightError, run_model_preflight
from hermes_orchestrator.read_models import build_run_summary
from hermes_orchestrator.registry import RoleRegistry

__all__ = [
    "PreflightError",
    "RoleRegistry",
    "RunOrchestrator",
    "assert_bundle_catalog_maps_resolve",
    "assert_known_workflow",
    "assert_persona_shelves_valid",
    "assert_taxonomy_keys_resolve",
    "build_run_summary",
    "load_yaml",
    "merge_policy_snapshot",
    "run_model_preflight",
]


def __getattr__(name: str) -> Any:
    if name == "RunOrchestrator":
        from hermes_orchestrator.pipeline import RunOrchestrator

        return RunOrchestrator
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
