from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent_core.mapping import mapping_or_empty
from config.model_routing_sections import (
    load_model_routing_doc,
    model_routing_path,
    routing_presets_mapping,
)


def list_routing_preset_summaries(repo_root: Path) -> list[dict[str, Any]]:
    presets = routing_presets_mapping(repo_root)
    rows: list[dict[str, Any]] = []
    for preset_id, raw in presets.items():
        if not isinstance(raw, dict):
            continue
        rows.append(
            {
                "id": str(preset_id),
                "label": str(raw.get("label") or preset_id),
                "description": str(raw.get("description") or ""),
            }
        )
    return rows


def apply_routing_preset(repo_root: Path, preset_id: str) -> dict[str, Any]:
    presets = routing_presets_mapping(repo_root)
    if preset_id not in presets or not isinstance(presets[preset_id], dict):
        raise KeyError(preset_id)
    chosen = dict(presets[preset_id])
    routing = load_model_routing_doc(repo_root)
    routing["routing_preset_id"] = preset_id
    cloud = mapping_or_empty(chosen.get("cloud_runtime"))
    if cloud:
        existing = mapping_or_empty(routing.get("cloud_runtime"))
        existing.update(cloud)
        routing["cloud_runtime"] = existing
    stages = mapping_or_empty(chosen.get("stage_providers"))
    if stages:
        routing["stage_providers"] = dict(stages)
    path = model_routing_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(routing, sort_keys=False), encoding="utf-8")
    return {
        "status": "applied",
        "preset_id": preset_id,
        "label": str(chosen.get("label") or preset_id),
        "routing_preset_id": preset_id,
        "cloud_runtime": mapping_or_empty(routing.get("cloud_runtime")),
        "stage_providers": mapping_or_empty(routing.get("stage_providers")),
    }
