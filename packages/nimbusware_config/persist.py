"""Load/persist config documents (file fallback vs Postgres authority)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

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
from nimbusware_extensions.custom_agents import CustomAgentRegistry, default_registry_path
from nimbusware_extensions.personas import PersonaShelf
from nimbusware_orchestrator.merge import atomic_write_yaml, load_yaml
from nimbusware_orchestrator.workflow_profiles import workflow_profile_path

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


def bundle_catalog_document_version(
    repo_root: Path,
    *,
    materializer: Any | None = None,
    raw: dict[str, Any] | None = None,
) -> int:
    if materializer is not None and getattr(materializer, "use_db", False):
        row = materializer.store.get(NS_POLICY, KEY_BUNDLE_CATALOG)
        return int(row.version) if row is not None else 1
    doc = raw if raw is not None else load_bundle_catalog_dict(repo_root, materializer=materializer)
    ver = doc.get("version") if isinstance(doc, dict) else None
    return int(ver) if ver is not None else 1


def persist_bundle_catalog_dict(
    repo_root: Path,
    content: dict[str, Any],
    *,
    materializer: Any | None = None,
    expected_version: int | None = None,
) -> int:
    if materializer is not None and getattr(materializer, "use_db", False):
        return int(
            materializer.upsert_content(
                NS_POLICY,
                KEY_BUNDLE_CATALOG,
                content,
                expected_version=expected_version,
            ),
        )
    current = bundle_catalog_document_version(repo_root, materializer=materializer)
    if expected_version is not None and expected_version != current:
        msg = f"bundle catalog version conflict: expected {expected_version}, current {current}"
        raise ValueError(msg)
    next_ver = current + 1
    content = dict(content)
    content["version"] = next_ver
    path = repo_root / "configs" / "bundles" / "catalog.yaml"
    atomic_write_yaml(path, content)
    return next_ver


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
