from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent_core.mapping import mapping_or_empty
from nimbusware_config.keys import KEY_USER_DEFAULTS, NS_MODEL_BINDINGS
from nimbusware_config.protocol import ConfigStore
from nimbusware_orchestrator.merge import atomic_write_yaml


def defaults_yaml_path(repo_root: Path) -> Path:
    return repo_root / "configs" / "model_bindings" / "defaults.yaml"


def load_defaults_file(repo_root: Path) -> dict[str, Any]:
    path = defaults_yaml_path(repo_root)
    if not path.is_file():
        return {"version": 1, "roles": {}}
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else {"version": 1, "roles": {}}


def load_user_defaults(repo_root: Path, store: ConfigStore | None = None) -> dict[str, Any]:
    if store is not None:
        row = store.get(NS_MODEL_BINDINGS, KEY_USER_DEFAULTS)
        if row is not None:
            return dict(row.content)
    return load_defaults_file(repo_root)


def save_user_defaults(
    repo_root: Path,
    content: dict[str, Any],
    *,
    store: ConfigStore | None = None,
) -> dict[str, Any]:
    doc = dict(content)
    if "version" not in doc:
        doc["version"] = 1
    roles = doc.get("roles")
    if not isinstance(roles, dict):
        msg = "roles must be an object"
        raise ValueError(msg)
    if store is not None:
        store.upsert(NS_MODEL_BINDINGS, KEY_USER_DEFAULTS, doc)
    path = defaults_yaml_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_yaml(path, doc)
    return doc


def list_binding_role_catalog(repo_root: Path) -> list[dict[str, Any]]:
    roles_path = repo_root / "configs" / "roles.yaml"
    out: list[dict[str, Any]] = []
    if roles_path.is_file():
        raw = yaml.safe_load(roles_path.read_text(encoding="utf-8"))
        entries = raw.get("roles") if isinstance(raw, dict) else None
        if isinstance(entries, list):
            for item in entries:
                if not isinstance(item, dict):
                    continue
                key = item.get("taxonomy_key")
                if not isinstance(key, str) or not key.strip():
                    continue
                out.append(
                    {
                        "agent_role": key.strip(),
                        "display_name": str(item.get("display_name") or key),
                        "kind": "builtin",
                    },
                )
    try:
        from nimbusware_extensions.custom_agents import CustomAgentRegistry, default_registry_path

        reg = CustomAgentRegistry.load(default_registry_path(repo_root))
        for agent in reg.list():
            out.append(
                {
                    "agent_role": agent.id,
                    "display_name": agent.display_name,
                    "kind": "custom",
                },
            )
    except ImportError:
        pass
    return sorted(out, key=lambda r: (r.get("kind") != "builtin", r.get("agent_role") or ""))


def merge_role_bindings(
    repo_root: Path,
    *,
    store: ConfigStore | None = None,
) -> list[dict[str, Any]]:
    defaults = load_user_defaults(repo_root, store=store)
    roles_doc = mapping_or_empty(defaults.get("roles"))
    catalog = list_binding_role_catalog(repo_root)
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in catalog:
        role = str(row["agent_role"])
        seen.add(role)
        binding = mapping_or_empty(roles_doc.get(role))
        merged.append(
            {
                **row,
                "binding": binding or None,
            },
        )
    for role, binding in roles_doc.items():
        if role in seen:
            continue
        merged.append(
            {
                "agent_role": role,
                "display_name": role,
                "kind": "custom",
                "binding": mapping_or_empty(binding),
            },
        )
    return merged
