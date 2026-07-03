from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

from agent_core.models.backlog import (
    BacklogEpic,
    BacklogFeature,
    BacklogMetadata,
    BacklogSlice,
    DeliveryBacklog,
    EpicStatus,
    SliceStatus,
    sync_backlog_metadata,
)
from orchestrator.backlog_heuristic_templates import (
    HEURISTIC_TEMPLATES,
    HeuristicSliceSpec,
    match_template_id,
)
from orchestrator.backlog_manifest import manifest_template_id
from orchestrator.stack_catalog import load_stack_catalog

_BACKLOG_GENERATOR_MODE: Literal["heuristic"] = "heuristic"


def _normalize_prompt(requirements: dict[str, Any] | None) -> str:
    if not isinstance(requirements, dict):
        return ""
    return str(requirements.get("business_prompt") or requirements.get("prompt") or "").strip()


def _catalog_template_id(prompt: str, repo_root: Path | None) -> str | None:
    if repo_root is None:
        return None
    catalog = repo_root / "configs" / "launch_eval" / "catalog.yaml"
    prompts_dir = repo_root / "configs" / "launch_eval" / "prompts"
    if not catalog.is_file() or not prompts_dir.is_dir():
        return None
    try:
        import yaml

        doc = yaml.safe_load(catalog.read_text(encoding="utf-8")) or {}
    except OSError:
        return None
    entries = doc.get("prompts")
    if not isinstance(entries, list):
        return None
    lower = prompt.lower()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        pid = str(entry.get("id") or "").strip()
        path_rel = str(entry.get("path") or "").strip()
        if not pid or not path_rel:
            continue
        prompt_path = prompts_dir / path_rel
        if not prompt_path.is_file():
            continue
        try:
            pdoc = yaml.safe_load(prompt_path.read_text(encoding="utf-8")) or {}
        except OSError:
            continue
        catalog_prompt = str(pdoc.get("business_prompt") or "").strip().lower()
        label = str(pdoc.get("label") or "").strip().lower()
        if catalog_prompt and catalog_prompt[:40] in lower:
            return pid if pid in HEURISTIC_TEMPLATES else match_template_id(catalog_prompt)
        if label and label in lower:
            return pid if pid in HEURISTIC_TEMPLATES else match_template_id(label)
    return None


def _discover_workspace_paths(repo_root: Path | None) -> list[str]:
    if repo_root is None:
        return []
    ws = Path(repo_root).resolve()
    if not ws.is_dir():
        return []
    from orchestrator.code_intel_entrypoints import (
        discover_entrypoint_modules,
        discover_test_seed_modules,
    )

    paths: list[str] = []
    paths.extend(discover_entrypoint_modules(ws))
    paths.extend(sorted(discover_test_seed_modules(ws)))
    for rel in ("index.html", "package.json", "pyproject.toml", "README.md"):
        if (ws / rel).is_file():
            paths.append(rel)
    for pattern in ("src/**/*.py", "src/**/*.tsx", "app/**/*.py", "packages/**/*.py"):
        for glob_path in sorted(ws.glob(pattern))[:12]:
            if any(part.startswith(".") for part in glob_path.parts):
                continue
            paths.append(str(glob_path.relative_to(ws)).replace("\\", "/"))
    seen: set[str] = set()
    out: list[str] = []
    for rel_path in paths:
        key = rel_path.replace("\\", "/")
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out[:24]


def _path_matches_suffix(path: str, suffix: str) -> bool:
    lower_path = path.lower().replace("\\", "/")
    token = suffix.lower().strip("/")
    if not token:
        return False
    if token.endswith("/"):
        return token.rstrip("/") in lower_path
    return token in lower_path


def _resolve_target_paths(
    spec: HeuristicSliceSpec,
    workspace_paths: list[str],
    *,
    fallback: tuple[str, ...],
) -> tuple[str, ...]:
    if not spec.target_suffixes:
        if workspace_paths:
            return (workspace_paths[0],)
        return fallback
    matched: list[str] = []
    for path in workspace_paths:
        if any(_path_matches_suffix(path, suf) for suf in spec.target_suffixes):
            matched.append(path)
    if matched:
        return tuple(matched[:3])
    guessed: list[str] = []
    for suf in spec.target_suffixes:
        token = suf.strip("/")
        if not token or token.endswith("/"):
            continue
        for path in workspace_paths:
            if _path_matches_suffix(path, token):
                guessed.append(path)
        if not guessed and not workspace_paths:
            guessed.append(token)
    if guessed:
        return tuple(dict.fromkeys(guessed))[:3]
    return fallback[:3] if fallback else (spec.target_suffixes[0],)


def _fallback_paths(repo_root: Path | None) -> tuple[str, ...]:
    discovered = _discover_workspace_paths(repo_root)
    if discovered:
        return tuple(discovered[:2])
    return ("app.py", "tests/")


def _title_from_prompt(prompt: str) -> str:
    if not prompt.strip():
        return "Campaign delivery"
    one_line = re.sub(r"\s+", " ", prompt.strip())
    return one_line[:120]


def generate_heuristic_backlog(
    campaign_id: str,
    *,
    requirements: dict[str, Any] | None = None,
    max_slices: int = 10,
    repo_root: Path | Any | None = None,
) -> DeliveryBacklog:
    prompt = _normalize_prompt(requirements)
    title = _title_from_prompt(prompt)
    root = Path(repo_root).resolve() if repo_root is not None else None
    template_id = (
        manifest_template_id(requirements)
        or _catalog_template_id(prompt, root)
        or match_template_id(prompt)
    )
    template = HEURISTIC_TEMPLATES.get(template_id) or HEURISTIC_TEMPLATES["generic"]
    manifest_stacks = {}
    if isinstance(requirements, dict):
        raw_manifest = requirements.get("stack_manifest")
        if isinstance(raw_manifest, dict):
            stacks_raw = raw_manifest.get("stacks")
            if isinstance(stacks_raw, dict):
                manifest_stacks = {str(k): str(v) for k, v in stacks_raw.items()}
    catalog = load_stack_catalog(root)
    workspace_paths = _discover_workspace_paths(root)
    fallback = _fallback_paths(root)
    count = max(1, min(max_slices, len(template.slices)))
    slices: list[BacklogSlice] = []
    prior_id: str | None = None
    for spec in template.slices[:count]:
        targets = _resolve_target_paths(spec, workspace_paths, fallback=fallback)
        deps: tuple[str, ...] = (prior_id,) if prior_id else ()
        stack_id = spec.stack_id
        if not stack_id and spec.surface_id and spec.surface_id in manifest_stacks:
            stack_id = manifest_stacks[spec.surface_id]
        allowed: tuple[str, ...] = ()
        if stack_id and stack_id in catalog:
            allowed = catalog[stack_id].allowed_globs
        slices.append(
            BacklogSlice(
                slice_id=spec.slice_id,
                status=SliceStatus.PENDING,
                target_paths=targets,
                depends_on=deps,
                estimated_loc=spec.estimated_loc,
                rationale=f"{spec.title}: {spec.rationale}",
                surface_id=spec.surface_id,
                stack_id=stack_id,
                allowed_globs=allowed,
            ),
        )
        prior_id = spec.slice_id
    backlog = DeliveryBacklog(
        campaign_id=campaign_id,
        epics=(
            BacklogEpic(
                epic_id=f"epic-{template.template_id}",
                title=title,
                status=EpicStatus.IN_PROGRESS,
                features=(
                    BacklogFeature(
                        feature_id=f"feat-{template.template_id}",
                        title=template.feature_title,
                        acceptance_criteria=template.acceptance,
                        slices=tuple(slices),
                    ),
                ),
            ),
        ),
        metadata=BacklogMetadata(generator_mode=_BACKLOG_GENERATOR_MODE),
    )
    return sync_backlog_metadata(backlog)
