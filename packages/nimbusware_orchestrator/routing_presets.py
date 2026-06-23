from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent_core.mapping import mapping_or_empty


def load_routing_presets(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "configs" / "routing_presets.yaml"
    if not path.is_file():
        return {"version": 1, "presets": {}}
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else {"version": 1, "presets": {}}


def list_routing_preset_summaries(repo_root: Path) -> list[dict[str, Any]]:
    doc = load_routing_presets(repo_root)
    presets = mapping_or_empty(doc.get("presets"))
    out: list[dict[str, Any]] = []
    for preset_id, raw in sorted(presets.items()):
        block = mapping_or_empty(raw)
        out.append(
            {
                "id": preset_id,
                "label": str(block.get("label") or preset_id),
                "description": str(block.get("description") or ""),
                "stage_providers": dict(mapping_or_empty(block.get("stage_providers"))),
                "cloud_enabled": bool(mapping_or_empty(block.get("cloud_runtime")).get("enabled")),
            },
        )
    return out


def apply_routing_preset(repo_root: Path, preset_id: str) -> dict[str, Any]:
    doc = load_routing_presets(repo_root)
    presets = mapping_or_empty(doc.get("presets"))
    block = mapping_or_empty(presets.get(preset_id))
    if not block:
        raise KeyError(preset_id)
    routing_path = repo_root / "configs" / "model-routing.yaml"
    routing = load_model_routing_yaml(routing_path)
    cloud_cfg = mapping_or_empty(block.get("cloud_runtime"))
    stage_providers = mapping_or_empty(block.get("stage_providers"))
    routing["cloud_runtime"] = {
        "enabled": bool(cloud_cfg.get("enabled")),
        "provider": str(cloud_cfg.get("provider") or "openai_compatible"),
        "base_url": str(cloud_cfg.get("base_url") or "https://api.openai.com/v1"),
        "api_key_env": str(cloud_cfg.get("api_key_env") or "OPENAI_API_KEY"),
        "model_id": str(cloud_cfg.get("model_id") or "gpt-4o-mini"),
        "health_path": str(cloud_cfg.get("health_path") or "/models"),
    }
    routing["stage_providers"] = dict(stage_providers)
    routing["routing_preset_id"] = preset_id
    write_model_routing_yaml(routing_path, routing)
    return {
        "preset_id": preset_id,
        "label": str(block.get("label") or preset_id),
        "cloud_enabled": bool(cloud_cfg.get("enabled")),
        "stage_providers": dict(stage_providers),
        "materialize_hint": "Restart API or run nimbusware-config materialize to reload routing",
    }


def load_model_routing_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"version": 1, "models": {}}
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else {"version": 1, "models": {}}


def write_model_routing_yaml(path: Path, content: dict[str, Any]) -> None:
    path.write_text(yaml.dump(content, sort_keys=False), encoding="utf-8")
