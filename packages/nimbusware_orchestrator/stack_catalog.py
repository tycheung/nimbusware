from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from nimbusware_env import find_repo_root

_SURFACE_WRITER = {
    "api": "backend_writer",
    "web": "frontend_writer",
    "mobile": "frontend_writer",
    "infra": "integration_adapter_writer",
    "deploy": "infra_writer",
    "contract": "planner",
}


@dataclass(frozen=True)
class StackDefinition:
    stack_id: str
    surface: str
    display_name: str
    workspace_subdir: str
    writer_role: str
    allowed_globs: tuple[str, ...]
    verify_commands: tuple[tuple[str, ...], ...]
    launch_framework_id: str | None = None
    max_files: int | None = None
    max_loc: int | None = None


def _parse_stack_doc(doc: dict[str, Any]) -> StackDefinition | None:
    if not isinstance(doc, dict):
        return None
    stack_id = str(doc.get("stack_id") or "").strip()
    surface = str(doc.get("surface") or "").strip()
    if not stack_id or not surface:
        return None
    writer = str(doc.get("writer_role") or _SURFACE_WRITER.get(surface, "backend_writer")).strip()
    globs_raw = doc.get("allowed_globs")
    globs = (
        tuple(str(g) for g in globs_raw if str(g).strip()) if isinstance(globs_raw, list) else ()
    )
    verify_raw = doc.get("verify_commands")
    verify: list[tuple[str, ...]] = []
    if isinstance(verify_raw, list):
        for row in verify_raw:
            if isinstance(row, list):
                cmd = tuple(str(p) for p in row if str(p).strip())
                if cmd:
                    verify.append(cmd)
    launch_id = str(doc.get("launch_framework_id") or "").strip() or None
    max_files_raw = doc.get("max_files")
    max_loc_raw = doc.get("max_loc")
    max_files = int(max_files_raw) if max_files_raw is not None else None
    max_loc = int(max_loc_raw) if max_loc_raw is not None else None
    return StackDefinition(
        stack_id=stack_id,
        surface=surface,
        display_name=str(doc.get("display_name") or stack_id).strip(),
        workspace_subdir=str(doc.get("workspace_subdir") or ".").strip() or ".",
        writer_role=writer,
        allowed_globs=globs,
        verify_commands=tuple(verify),
        launch_framework_id=launch_id,
        max_files=max_files,
        max_loc=max_loc,
    )


def load_stack_catalog(repo_root: Path | None = None) -> dict[str, StackDefinition]:
    root = repo_root or find_repo_root()
    catalog_path = root / "configs" / "stacks" / "catalog.yaml"
    if not catalog_path.is_file():
        return {}
    try:
        catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or {}
    except OSError:
        return {}
    entries = catalog.get("stacks")
    if not isinstance(entries, list):
        return {}
    out: dict[str, StackDefinition] = {}
    stacks_dir = catalog_path.parent
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        stack_id = str(entry.get("id") or "").strip()
        rel = str(entry.get("path") or "").strip()
        if not stack_id or not rel:
            continue
        stack_path = stacks_dir / rel
        if not stack_path.is_file():
            continue
        try:
            doc = yaml.safe_load(stack_path.read_text(encoding="utf-8")) or {}
        except OSError:
            continue
        parsed = _parse_stack_doc(doc)
        if parsed is not None:
            out[stack_id] = parsed
    return out


def resolve_manifest_stacks(
    manifest: dict[str, Any] | None,
    *,
    repo_root: Path | None = None,
) -> dict[str, StackDefinition]:
    if not isinstance(manifest, dict):
        return {}
    catalog = load_stack_catalog(repo_root)
    stacks_raw = manifest.get("stacks")
    if not isinstance(stacks_raw, dict):
        return {}
    resolved: dict[str, StackDefinition] = {}
    for surface, stack_id in stacks_raw.items():
        sid = str(stack_id or "").strip()
        if not sid:
            continue
        stack = catalog.get(sid)
        if stack is not None:
            resolved[str(surface)] = stack
    return resolved


def stack_for_surface(
    manifest: dict[str, Any] | None,
    surface_id: str,
    *,
    repo_root: Path | None = None,
) -> StackDefinition | None:
    if not isinstance(manifest, dict):
        return None
    stacks_raw = manifest.get("stacks")
    if not isinstance(stacks_raw, dict):
        return None
    stack_id = str(stacks_raw.get(surface_id) or "").strip()
    if not stack_id:
        return None
    return load_stack_catalog(repo_root).get(stack_id)


def writer_role_for_surface(surface_id: str) -> str:
    return _SURFACE_WRITER.get(surface_id.strip().lower(), "backend_writer")
