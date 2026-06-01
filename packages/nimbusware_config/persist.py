"""Load/persist config documents (file fallback vs Postgres authority)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from hermes_extensions.custom_agents import CustomAgentRegistry, default_registry_path
from hermes_extensions.personas import PersonaShelf
from hermes_orchestrator.merge import atomic_write_yaml, load_yaml
from hermes_orchestrator.workflow_profiles import workflow_profile_path
from nimbusware_config.keys import (
    KEY_BUNDLE_CATALOG,
    KEY_CUSTOM_AGENTS_REGISTRY,
    KEY_MODEL_ROUTING,
    KEY_PERSONA_SHELVES,
    NS_CUSTOM_AGENTS,
    NS_PERSONAS,
    NS_POLICY,
    NS_WORKFLOWS,
)

_MODEL_ROUTING_PATH = ("configs", "model-routing.yaml")


def load_model_routing_dict(
    repo_root: Path,
    *,
    materializer: Any | None = None,
) -> dict[str, Any]:
    if materializer is not None and getattr(materializer, "use_db", False):
        return cast(dict[str, Any], materializer.get_model_routing_base())
    path = repo_root.joinpath(*_MODEL_ROUTING_PATH)
    return load_yaml(path)


def persist_model_routing_dict(
    repo_root: Path,
    content: dict[str, Any],
    *,
    materializer: Any | None = None,
) -> None:
    if materializer is not None and getattr(materializer, "use_db", False):
        materializer.upsert_content(NS_POLICY, KEY_MODEL_ROUTING, content)
        return
    path = repo_root.joinpath(*_MODEL_ROUTING_PATH)
    atomic_write_yaml(path, content)


def load_persona_shelf(
    repo_root: Path,
    *,
    materializer: Any | None = None,
) -> PersonaShelf:
    if materializer is not None and getattr(materializer, "use_db", False):
        return cast(PersonaShelf, materializer.get_persona_shelf())
    path = repo_root / "configs" / "personas" / "shelves.yaml"
    return PersonaShelf(path)


def persist_persona_shelf(
    repo_root: Path,
    shelf: PersonaShelf,
    *,
    materializer: Any | None = None,
) -> None:
    if materializer is not None and getattr(materializer, "use_db", False):
        materializer.upsert_content(NS_PERSONAS, KEY_PERSONA_SHELVES, shelf.raw)
        return
    path = repo_root / "configs" / "personas" / "shelves.yaml"
    atomic_write_yaml(path, shelf.raw)


def load_workflow_profile_dict(
    repo_root: Path,
    profile: str,
    *,
    materializer: Any | None = None,
) -> dict[str, Any]:
    if materializer is not None and getattr(materializer, "use_db", False):
        return cast(dict[str, Any], materializer.get_workflow_profile_dict(profile))
    return load_yaml(workflow_profile_path(repo_root, profile))


def load_bundle_catalog_dict(
    repo_root: Path,
    *,
    materializer: Any | None = None,
) -> dict[str, Any]:
    if materializer is not None and getattr(materializer, "use_db", False):
        return cast(dict[str, Any], materializer.get_bundle_catalog())
    path = repo_root / "configs" / "bundles" / "catalog.yaml"
    return load_yaml(path)


def persist_bundle_catalog_dict(
    repo_root: Path,
    content: dict[str, Any],
    *,
    materializer: Any | None = None,
) -> None:
    if materializer is not None and getattr(materializer, "use_db", False):
        materializer.upsert_content(NS_POLICY, KEY_BUNDLE_CATALOG, content)
        return
    path = repo_root / "configs" / "bundles" / "catalog.yaml"
    atomic_write_yaml(path, content)


def load_custom_agent_registry(
    repo_root: Path,
    *,
    materializer: Any | None = None,
) -> CustomAgentRegistry:
    if materializer is not None and getattr(materializer, "use_db", False):
        return cast(CustomAgentRegistry, materializer.get_custom_agent_registry())
    return CustomAgentRegistry.load(default_registry_path(repo_root))


def persist_custom_agent_registry(
    repo_root: Path,
    registry: CustomAgentRegistry,
    *,
    materializer: Any | None = None,
) -> None:
    if materializer is not None and getattr(materializer, "use_db", False):
        materializer.upsert_content(
            NS_CUSTOM_AGENTS,
            KEY_CUSTOM_AGENTS_REGISTRY,
            registry.to_content(),
        )
        return
    registry.save(default_registry_path(repo_root))


def persist_workflow_profile_dict(
    repo_root: Path,
    profile: str,
    content: dict[str, Any],
    *,
    materializer: Any | None = None,
) -> None:
    key = profile.strip()
    if materializer is not None and getattr(materializer, "use_db", False):
        materializer.upsert_content(NS_WORKFLOWS, key, content)
        return
    atomic_write_yaml(workflow_profile_path(repo_root, key), content)
