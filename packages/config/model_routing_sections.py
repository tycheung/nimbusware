"""Load model-routing.yaml sections; deprecated config paths alias here."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent_core.mapping import mapping_or_empty

_MODEL_ROUTING_REL = Path("configs") / "model-routing.yaml"
_DEPRECATED_PATHS: dict[str, Path] = {
    "model_policy": Path("configs") / "model_policy.yaml",
    "providers": Path("configs") / "model_providers.yaml",
    "model_bindings": Path("configs") / "model_bindings" / "defaults.yaml",
    "routing_presets": Path("configs") / "routing_presets.yaml",
}


def model_routing_path(repo_root: Path) -> Path:
    return repo_root / _MODEL_ROUTING_REL


def _read_yaml_dict(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else None


def load_model_routing_doc(repo_root: Path) -> dict[str, Any]:
    doc = _read_yaml_dict(model_routing_path(repo_root))
    return doc if doc is not None else {"version": 1}


def _routing_section(repo_root: Path, section_key: str) -> dict[str, Any] | None:
    routing = load_model_routing_doc(repo_root)
    section = routing.get(section_key)
    if isinstance(section, dict):
        return section
    if section_key == "providers":
        providers = routing.get("providers")
        if isinstance(providers, list):
            return {"providers": providers}
    return None


def _deprecated_section(repo_root: Path, section_key: str) -> dict[str, Any] | None:
    rel = _DEPRECATED_PATHS.get(section_key)
    if rel is None:
        return None
    return _read_yaml_dict(repo_root / rel)


def _resolve_section(
    repo_root: Path,
    section_key: str,
    *,
    default: dict[str, Any],
) -> dict[str, Any]:
    canonical = _routing_section(repo_root, section_key)
    if canonical is not None:
        return canonical
    deprecated = _deprecated_section(repo_root, section_key)
    if deprecated is not None:
        return deprecated
    return dict(default)


def default_model_policy_doc() -> dict[str, Any]:
    return {
        "version": 1,
        "allowed_cloud_providers": [],
        "require_admin_for_cloud_swap": False,
        "blocked_model_ids": [],
        "audit_include_binding_events": True,
    }


def load_model_policy_doc(repo_root: Path) -> dict[str, Any]:
    return _resolve_section(repo_root, "model_policy", default=default_model_policy_doc())


def load_provider_catalog_doc(repo_root: Path) -> dict[str, Any]:
    return _resolve_section(repo_root, "providers", default={"providers": []})


def load_model_bindings_defaults_doc(repo_root: Path) -> dict[str, Any]:
    return _resolve_section(repo_root, "model_bindings", default={"version": 1, "roles": {}})


def load_routing_preset_catalog_doc(repo_root: Path) -> dict[str, Any]:
    return _resolve_section(repo_root, "routing_presets", default={"version": 1, "presets": {}})


def routing_presets_mapping(repo_root: Path) -> dict[str, Any]:
    doc = load_routing_preset_catalog_doc(repo_root)
    return dict(mapping_or_empty(doc.get("presets")))
