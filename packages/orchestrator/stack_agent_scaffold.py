from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from extensions.custom_agents import (
    CustomAgent,
    CustomAgentRegistry,
    default_registry_path,
)
from orchestrator.stack_catalog import load_stack_catalog, stack_for_surface


def _agent_scaffold_block(stack_doc_path: Path) -> dict[str, str]:
    if not stack_doc_path.is_file():
        return {}
    raw = yaml.safe_load(stack_doc_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}
    block = raw.get("agent_scaffold")
    if not isinstance(block, dict):
        return {}
    prompt = str(block.get("system_prompt") or "").strip()
    if not prompt:
        return {}
    return {
        "system_prompt": prompt,
        "description": str(block.get("description") or "").strip(),
    }


def scaffold_agents_for_manifest(
    manifest: dict[str, Any],
    *,
    repo_root: Path,
    persist: bool = True,
) -> list[str]:
    stacks_raw = manifest.get("stacks")
    if not isinstance(stacks_raw, dict):
        return []
    catalog = load_stack_catalog(repo_root)
    stacks_dir = repo_root / "configs" / "stacks"
    registry = CustomAgentRegistry.load(default_registry_path(repo_root))
    created: list[str] = []
    for surface_id, stack_id in stacks_raw.items():
        stack = catalog.get(str(stack_id)) or stack_for_surface(
            manifest, str(surface_id), repo_root=repo_root
        )
        if stack is None:
            continue
        doc_path = stacks_dir / f"{stack.stack_id}.yaml"
        scaffold = _agent_scaffold_block(doc_path)
        if not scaffold:
            continue
        agent_id = f"{stack.stack_id}_writer"
        registry.upsert(
            CustomAgent(
                id=agent_id,
                display_name=f"{stack.display_name} writer",
                system_prompt=scaffold["system_prompt"],
                description=scaffold.get("description", ""),
                bound_role_id=stack.writer_role,
            ),
        )
        created.append(agent_id)
    if persist and created:
        registry.save(default_registry_path(repo_root))
    return created
