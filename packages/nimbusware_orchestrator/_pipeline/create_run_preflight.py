from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_orchestrator.registry import RoleRegistry


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
    import nimbusware_orchestrator.pipeline as pipeline

    pipeline.assert_known_workflow(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    pipeline.assert_stage_graph_valid(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    pipeline.assert_bundle_catalog_maps_resolve(repo_root)
    pipeline.assert_persona_shelves_valid(repo_root, config_materializer=config_materializer)
    pipeline.assert_agent_evaluator_persona_in_shelves(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    if business_area_persona_id or development_role_persona_id:
        from nimbusware_config.persist import load_persona_shelf
        from nimbusware_orchestrator.ingress import assert_persona_assignment_valid

        shelf = load_persona_shelf(repo_root, materializer=config_materializer)
        assert_persona_assignment_valid(
            shelf,
            business_area_persona_id=business_area_persona_id,
            development_role_persona_id=development_role_persona_id,
        )
    pipeline.assert_taxonomy_keys_resolve(
        registry,
        pipeline.taxonomy_keys_for_run_lifecycle(registry, critique_router),
    )
    critique_coverage = pipeline.critique_coverage_snapshot(registry, critique_router)
    pipeline.assert_critique_coverage_complete(critique_coverage)
    return critique_coverage
