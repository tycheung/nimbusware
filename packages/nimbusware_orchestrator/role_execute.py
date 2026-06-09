"""Dispatch single Role Registry roles for admin debug execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from nimbusware_orchestrator.registry import RoleRegistry

_SUPPORTED_PRODUCERS = frozenset(
    {
        "planner",
        "backend_writer",
        "frontend_writer",
        "test_writer",
        "agent_evaluator",
        "module_integrator",
        "integration_adapter_writer",
        "domain_researcher",
        "code_researcher",
        "stitcher",
    },
)


def resolve_taxonomy_key(registry: RoleRegistry, role_id: str) -> str:
    raw = role_id.strip()
    try:
        uid = UUID(raw)
        key = registry.taxonomy_key_for(uid)
        if key:
            return key
    except ValueError:
        pass
    key = raw.lower()
    registry.resolve(key)
    return key


def supported_role_taxonomy_keys(registry: RoleRegistry) -> list[str]:
    keys = sorted(k for k in registry.known_taxonomy_keys() if k in _SUPPORTED_PRODUCERS)
    return keys


def dispatch_role_execute(
    orch: Any,
    run_id: UUID,
    taxonomy_key: str,
    *,
    workspace: Path | None = None,
) -> dict[str, Any]:
    key = taxonomy_key.strip().lower()
    if key not in _SUPPORTED_PRODUCERS:
        msg = f"role execute not supported for taxonomy_key={key!r}"
        raise ValueError(msg)

    stage_name = key
    if key == "planner":
        orch.execute_plan_stage(run_id)
    elif key in ("backend_writer", "frontend_writer", "test_writer"):
        stage_name = "writers.verify"
        orch.execute_writer_verifier_pass(run_id, workspace=workspace)
    elif key == "agent_evaluator":
        orch._maybe_emit_agent_evaluator_stage(run_id)
    elif key == "module_integrator":
        stage_name = "integrator.gate"
        orch._emit_bundle_integrator_gate(run_id)
    elif key == "integration_adapter_writer":
        orch._maybe_emit_integration_adapter_writer_stage(run_id)
    elif key in ("domain_researcher", "code_researcher"):
        stage_name = "research"
        orch._maybe_emit_research_stages(run_id)
    elif key == "stitcher":
        stage_name = "stitch"
        orch._maybe_emit_stitch_stages(run_id)
    else:
        raise ValueError(f"unsupported role: {key}")

    return {
        "status": "executed",
        "taxonomy_key": key,
        "stage_name": stage_name,
        "run_id": str(run_id),
    }
