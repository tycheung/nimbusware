from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.critique.routing import (
    assert_critique_coverage_complete,
    critique_coverage_snapshot,
    taxonomy_keys_for_run_lifecycle,
)
from orchestrator.ingress import (
    assert_agent_evaluator_persona_in_shelves,
    assert_bundle_catalog_maps_resolve,
    assert_known_workflow,
    assert_persona_shelves_valid,
    assert_stage_graph_valid,
    assert_taxonomy_keys_resolve,
)
from orchestrator.registry import RoleRegistry


def assert_create_run_preflight(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None,
    registry: RoleRegistry,
    critique_router: Any,
    business_area_persona_id: str | None = None,
    development_role_persona_id: str | None = None,
) -> dict[str, Any]:
    assert_known_workflow(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    assert_stage_graph_valid(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    assert_bundle_catalog_maps_resolve(repo_root)
    assert_persona_shelves_valid(repo_root, config_materializer=config_materializer)
    assert_agent_evaluator_persona_in_shelves(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    if business_area_persona_id or development_role_persona_id:
        from config.persist import load_persona_shelf
        from orchestrator.ingress import assert_persona_assignment_valid

        shelf = load_persona_shelf(repo_root, materializer=config_materializer)
        assert_persona_assignment_valid(
            shelf,
            business_area_persona_id=business_area_persona_id,
            development_role_persona_id=development_role_persona_id,
        )
    assert_taxonomy_keys_resolve(
        registry,
        taxonomy_keys_for_run_lifecycle(registry, critique_router),
    )
    critique_coverage = critique_coverage_snapshot(registry, critique_router)
    assert_critique_coverage_complete(critique_coverage)
    return critique_coverage
