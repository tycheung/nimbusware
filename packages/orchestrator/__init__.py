"""YAML merge, Role Registry, preflight, and MVP orchestration.

Avoid importing ``pipeline`` at package import time: ``pipeline`` depends on
``extensions``, while ``extensions`` (e.g. ``catalog``) imports
``orchestrator.merge`` — eager ``pipeline`` import would create a cycle.
``RunOrchestrator`` is exposed lazily via :pep:`562` ``__getattr__``.
"""

from __future__ import annotations

from typing import Any

from orchestrator.ingress import (
    assert_bundle_catalog_maps_resolve,
    assert_known_workflow,
    assert_persona_shelves_valid,
    assert_taxonomy_keys_resolve,
)
from orchestrator.merge import load_yaml, merge_policy_snapshot
from orchestrator.preflight import PreflightError, run_model_preflight
from orchestrator.registry import RoleRegistry
from projections.run_summary import build_run_summary

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
    "try_broker_capacity_probe",
    "try_broker_compute_work",
]


def __getattr__(name: str) -> Any:
    if name == "RunOrchestrator":
        from orchestrator.pipeline import RunOrchestrator

        return RunOrchestrator
    if name == "try_broker_compute_work":
        from orchestrator.compute_broker_bridge import try_broker_compute_work

        return try_broker_compute_work
    if name == "try_broker_capacity_probe":
        from orchestrator.capacity_broker_bridge import try_broker_capacity_probe

        return try_broker_capacity_probe
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
