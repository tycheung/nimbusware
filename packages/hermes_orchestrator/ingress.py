"""Validate external labels before emitting orchestrator events."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes_extensions.personas import ALLOWED_SHELVES, PersonaShelf
from hermes_orchestrator.registry import RoleRegistry
from hermes_orchestrator.workflow_agent_evaluator import parse_agent_evaluator_workflow_block
from hermes_orchestrator.workflow_profiles import workflow_profile_path


def assert_bundle_catalog_maps_resolve(repo_root: Path) -> None:
    """Raise if catalog ``workflow_bundle_map`` targets unknown ``bundles[].id`` values."""
    # Deferred import avoids circular init with hermes_extensions.catalog.
    from hermes_extensions.catalog import assert_workflow_bundle_map_ids_resolve

    assert_workflow_bundle_map_ids_resolve(repo_root / "configs" / "bundles" / "catalog.yaml")


def assert_persona_shelves_valid(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> None:
    """Raise if persona shelves are missing or structurally invalid."""
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        config_materializer.get_persona_shelf()
        return
    path = repo_root / "configs" / "personas" / "shelves.yaml"
    if not path.is_file():
        msg = f"missing persona catalog shelves: {path}"
        raise FileNotFoundError(msg)
    PersonaShelf(path).validate_structure()


def assert_agent_evaluator_persona_in_shelves(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
) -> None:
    """When workflow ``agent_evaluator.enabled``, require catalog-backed ``persona_id``.

    The reserved slug ``default`` is allowed without appearing on shelves (generic eval slot /
    workflows that omit a concrete catalog persona id).
    """
    block = parse_agent_evaluator_workflow_block(
        repo_root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    if not block.enabled:
        return
    if block.persona_id == "default":
        return
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        shelf = config_materializer.get_persona_shelf()
    else:
        path = repo_root / "configs" / "personas" / "shelves.yaml"
        shelf = PersonaShelf(path)
    known = shelf.all_persona_ids()
    if block.persona_id in known:
        return
    ac = block.auto_create_persona
    if (
        ac.enabled
        and str(ac.shelf).strip() in ALLOWED_SHELVES
        and bool(str(ac.display_name).strip())
    ):
        return
    msg = (
        "agent_evaluator.persona_id must be 'default' or a persona id from "
        f"configs/personas/shelves.yaml (got {block.persona_id!r}; known={sorted(known)})"
    )
    raise ValueError(msg)


def assert_known_workflow(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
) -> None:
    """Raise ``FileNotFoundError`` / ``ValueError`` if workflow profile is missing or invalid."""
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        config_materializer.get_workflow_profile_dict(workflow_profile)
        return
    workflow_profile_path(repo_root, workflow_profile)


def assert_stage_graph_valid(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
) -> None:
    """When workflow defines ``stage_graph``, validate DAG (cycles, unknown stages)."""
    from hermes_orchestrator.stage_graph import (
        KNOWN_STAGE_GRAPH_STAGES,
        stage_graph_from_workflow_profile,
        validate_stage_graph,
    )
    from hermes_orchestrator.workflow_profiles import workflow_profile_dict

    raw = workflow_profile_dict(
        repo_root,
        workflow_profile,
        materializer=config_materializer,
    )
    if "stage_graph" not in raw:
        return
    graph = stage_graph_from_workflow_profile(raw)
    validate_stage_graph(graph, KNOWN_STAGE_GRAPH_STAGES)


def assert_persona_assignment_valid(
    shelf: PersonaShelf,
    *,
    business_area_persona_id: str | None = None,
    development_role_persona_id: str | None = None,
) -> None:
    """Validate optional composite persona ids exist on the correct shelves (§3B.3)."""
    if business_area_persona_id is not None:
        bid = str(business_area_persona_id).strip()
        if bid and shelf.find_entry("business_area", bid) is None:
            msg = f"business_area_persona_id {bid!r} not found on business_area shelf"
            raise ValueError(msg)
    if development_role_persona_id is not None:
        did = str(development_role_persona_id).strip()
        if did and shelf.find_entry("development_role", did) is None:
            msg = f"development_role_persona_id {did!r} not found on development_role shelf"
            raise ValueError(msg)


def assert_taxonomy_keys_resolve(registry: RoleRegistry, keys: list[str]) -> None:
    """Raise ``KeyError`` if any taxonomy key is unknown."""
    for k in keys:
        registry.resolve(k)
