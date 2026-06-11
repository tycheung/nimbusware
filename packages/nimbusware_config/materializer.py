from __future__ import annotations

import copy
from pathlib import Path
from typing import Any
from uuid import UUID

from nimbusware_config.flags import config_from_db_enabled
from nimbusware_config.keys import (
    KEY_BUNDLE_CATALOG,
    KEY_CRITIQUE_PAIRINGS,
    KEY_CUSTOM_AGENTS_REGISTRY,
    KEY_ESCALATION,
    KEY_INTEGRATOR_THRESHOLDS,
    KEY_MODEL_ROUTING,
    KEY_PERSONA_SHELVES,
    KEY_ROLE_REGISTRY,
    KEY_SELF_REFINEMENT,
    NS_CRITIC_PACKS,
    NS_CUSTOM_AGENTS,
    NS_PERSONAS,
    NS_POLICY,
    NS_ROLES,
    NS_WORKFLOWS,
)
from nimbusware_config.protocol import ConfigStore
from nimbusware_config.store import (
    InMemoryConfigStore,
    PostgresConfigStore,
    _maybe_publish_config_notify,
)
from nimbusware_extensions.custom_agents import CustomAgentRegistry
from nimbusware_extensions.personas import PersonaShelf
from nimbusware_orchestrator.merge import load_yaml
from nimbusware_orchestrator.registry import RoleRegistry


class ConfigMaterializer:
    """Materialized configuration for orchestrator and API."""

    def __init__(
        self,
        repo_root: Path,
        store: ConfigStore | None = None,
        *,
        use_db: bool | None = None,
    ) -> None:
        self._repo_root = repo_root.resolve()
        self._use_db = config_from_db_enabled() if use_db is None else use_db
        if store is not None:
            self._store = store
        elif self._use_db:
            import os

            url = os.environ.get("NIMBUSWARE_DATABASE_URL", "").strip()
            if not url:
                msg = "NIMBUSWARE_DATABASE_URL required when config store uses Postgres"
                raise ValueError(msg)
            self._store = PostgresConfigStore(url)
        else:
            self._store = InMemoryConfigStore()
        self._generation = 0
        self._cache: dict[tuple[str, str], dict[str, Any]] = {}

    @property
    def use_db(self) -> bool:
        return self._use_db

    @property
    def store(self) -> ConfigStore:
        return self._store

    @property
    def generation(self) -> int:
        return self._generation

    def refresh(self, namespace: str | None = None) -> None:
        """Invalidate cache; optional ``namespace`` scopes the bust."""
        self._generation += 1
        if namespace is None:
            self._cache.clear()
            return
        for key in list(self._cache):
            if key[0] == namespace:
                del self._cache[key]

    def _get_content(self, namespace: str, document_key: str) -> dict[str, Any]:
        cache_key = (namespace, document_key)
        if cache_key in self._cache:
            return copy.deepcopy(self._cache[cache_key])
        if self._use_db:
            row = self._store.get(namespace, document_key)
            if row is None:
                msg = f"missing config document: {namespace}/{document_key}"
                raise KeyError(msg)
            content = copy.deepcopy(row.content)
        else:
            content = self._load_from_files(namespace, document_key)
        self._cache[cache_key] = content
        return copy.deepcopy(content)

    def _load_from_files(self, namespace: str, document_key: str) -> dict[str, Any]:
        if namespace == NS_PERSONAS and document_key == KEY_PERSONA_SHELVES:
            return load_yaml(self._repo_root / "configs" / "personas" / "shelves.yaml")
        if namespace == NS_ROLES and document_key == KEY_ROLE_REGISTRY:
            return load_yaml(self._repo_root / "configs" / "roles.yaml")
        if namespace == NS_POLICY and document_key == KEY_MODEL_ROUTING:
            base, _ = _default_paths(self._repo_root)
            return load_yaml(base)
        if namespace == NS_POLICY and document_key == KEY_ESCALATION:
            return load_yaml(self._repo_root / "configs" / "escalation" / "policy.yaml")
        if namespace == NS_POLICY and document_key == KEY_INTEGRATOR_THRESHOLDS:
            return load_yaml(self._repo_root / "configs" / "integrator" / "thresholds.yaml")
        if namespace == NS_POLICY and document_key == KEY_SELF_REFINEMENT:
            return load_yaml(self._repo_root / "configs" / "self_refinement" / "policy.yaml")
        if namespace == NS_POLICY and document_key == KEY_BUNDLE_CATALOG:
            return load_yaml(self._repo_root / "configs" / "bundles" / "catalog.yaml")
        if namespace == NS_PERSONAS and document_key == KEY_CRITIQUE_PAIRINGS:
            return load_yaml(self._repo_root / "configs" / "personas" / "critique_pairings.yaml")
        if namespace == NS_WORKFLOWS:
            path = self._repo_root / "configs" / "workflows" / f"{document_key}.yaml"
            return load_yaml(path)
        if namespace == NS_CUSTOM_AGENTS and document_key == KEY_CUSTOM_AGENTS_REGISTRY:
            path = self._repo_root / "configs" / "custom_agents" / "registry.yaml"
            if path.is_file():
                return load_yaml(path)
            return {"agents": []}
        if namespace == NS_CRITIC_PACKS:
            path = self._repo_root / "configs" / "critic_packs" / f"{document_key}.yaml"
            return load_yaml(path)
        msg = f"unknown config file mapping: {namespace}/{document_key}"
        raise KeyError(msg)

    def upsert_content(
        self,
        namespace: str,
        document_key: str,
        content: dict[str, Any],
        *,
        expected_version: int | None = None,
    ) -> int:
        """Persist and refresh materialized cache; return new row version."""
        if not self._use_db:
            msg = "upsert_content requires Postgres config mode"
            raise RuntimeError(msg)
        row = self._store.upsert(
            namespace,
            document_key,
            content,
            expected_version=expected_version,
        )
        self._cache[(namespace, document_key)] = copy.deepcopy(content)
        self._generation += 1
        _maybe_publish_config_notify(namespace, document_key, row.version)
        return row.version

    def get_persona_shelf(self) -> PersonaShelf:
        raw = self._get_content(NS_PERSONAS, KEY_PERSONA_SHELVES)
        shelf = PersonaShelf.from_content(raw)
        shelf.validate_structure()
        return shelf

    def get_role_registry(self) -> RoleRegistry:
        raw = self._get_content(NS_ROLES, KEY_ROLE_REGISTRY)
        return _role_registry_from_content(raw)

    def get_workflow_profile_dict(self, profile: str) -> dict[str, Any]:
        key = profile.strip()
        return self._get_content(NS_WORKFLOWS, key)

    def list_workflow_profile_keys(self) -> list[str]:
        if self._use_db:
            return self._store.list_keys(NS_WORKFLOWS)
        wf_dir = self._repo_root / "configs" / "workflows"
        if not wf_dir.is_dir():
            return []
        out: list[str] = []
        for path in sorted(wf_dir.glob("*.yaml")):
            out.append(path.stem)
        for path in sorted(wf_dir.glob("*.yml")):
            if path.stem not in out:
                out.append(path.stem)
        return out

    def get_model_routing_base(self) -> dict[str, Any]:
        return self._get_content(NS_POLICY, KEY_MODEL_ROUTING)

    def get_escalation_policy(self) -> dict[str, Any]:
        return self._get_content(NS_POLICY, KEY_ESCALATION)

    def get_integrator_thresholds(self) -> dict[str, Any]:
        return self._get_content(NS_POLICY, KEY_INTEGRATOR_THRESHOLDS)

    def get_self_refinement_policy(self) -> dict[str, Any]:
        return self._get_content(NS_POLICY, KEY_SELF_REFINEMENT)

    def get_critique_pairings(self) -> dict[str, Any]:
        return self._get_content(NS_PERSONAS, KEY_CRITIQUE_PAIRINGS)

    def get_bundle_catalog(self) -> dict[str, Any]:
        return self._get_content(NS_POLICY, KEY_BUNDLE_CATALOG)

    def get_custom_agent_registry(self) -> CustomAgentRegistry:
        raw = self._get_content(NS_CUSTOM_AGENTS, KEY_CUSTOM_AGENTS_REGISTRY)
        return CustomAgentRegistry.from_content(raw)

    def list_critic_pack_ids(self) -> list[str]:
        if self._use_db:
            return self._store.list_keys(NS_CRITIC_PACKS)
        root = self._repo_root / "configs" / "critic_packs"
        if not root.is_dir():
            return []
        return sorted(p.stem for p in root.glob("*.yaml"))

    def get_critic_pack(self, pack_id: str) -> dict[str, Any]:
        return self._get_content(NS_CRITIC_PACKS, pack_id.strip())

    def upsert_critic_pack(self, pack_id: str, content: dict[str, Any]) -> int:
        return self.upsert_content(NS_CRITIC_PACKS, pack_id.strip(), content)


def _default_paths(repo_root: Path) -> tuple[Path, Path]:
    from nimbusware_orchestrator.pipeline import default_paths

    return default_paths(repo_root)


def _role_registry_from_content(raw: dict[str, Any]) -> RoleRegistry:
    entries = raw.get("roles")
    if not isinstance(entries, list):
        msg = "roles registry content must contain a 'roles' list"
        raise ValueError(msg)
    yaml_version = int(raw.get("version", 0))
    mapping: dict[str, UUID] = {}
    for item in entries:
        if not isinstance(item, dict):
            continue
        key = item.get("taxonomy_key")
        rid = item.get("role_id")
        if isinstance(key, str) and rid:
            mapping[key.strip().lower()] = UUID(str(rid))
    import hashlib
    import json

    digest = hashlib.sha256(
        json.dumps(raw, sort_keys=True, separators=(",", ":")).encode(),
    ).hexdigest()[:16]
    return RoleRegistry.from_mapping(
        mapping,
        yaml_version=yaml_version,
        content_digest_sha256_16=digest,
    )
