"""Load launch eval prompt catalog from configs/launch_eval/catalog.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from nimbusware_env import find_repo_root


def catalog_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "launch_eval" / "catalog.yaml"


def load_launch_eval_catalog(repo_root: Path | None = None) -> dict[str, Any]:
    path = catalog_path(repo_root)
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def default_workspace_paths(repo_root: Path | None = None) -> tuple[Path, ...]:
    root = repo_root or find_repo_root()
    doc = load_launch_eval_catalog(root)
    paths: list[Path] = []
    for entry in doc.get("default_workspaces") or []:
        rel = Path(str(entry))
        candidate = rel if rel.is_absolute() else (root / rel)
        paths.append(candidate.resolve())
    return tuple(paths)


def prompt_ids(repo_root: Path | None = None) -> tuple[str, ...]:
    doc = load_launch_eval_catalog(repo_root)
    return tuple(str(p["id"]) for p in doc.get("prompts") or [] if p.get("id"))


def load_prompt_entries(repo_root: Path | None = None) -> list[dict[str, Any]]:
    root = repo_root or find_repo_root()
    doc = load_launch_eval_catalog(root)
    entries: list[dict[str, Any]] = []
    for ref in doc.get("prompts") or []:
        rel = str(ref.get("path") or "").strip()
        pid = str(ref.get("id") or "").strip()
        if not rel:
            continue
        path = root / "configs" / "launch_eval" / rel
        if not path.is_file():
            continue
        entry = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if pid and not entry.get("id"):
            entry["id"] = pid
        entries.append(entry)
    return entries


def _word_overlap(a: str, b: str) -> int:
    return len(set(a.split()) & set(b.split()))


def match_prompt_id(business_prompt: str, repo_root: Path | None = None) -> str | None:
    text = business_prompt.strip().lower()
    if not text:
        return None
    best_score = 0
    best_id: str | None = None
    for entry in load_prompt_entries(repo_root):
        pid = str(entry.get("id") or "").strip()
        if not pid:
            continue
        label = str(entry.get("label") or "").lower()
        catalog_prompt = str(entry.get("business_prompt") or "").lower().strip()
        score = 0
        if pid.replace("_", " ") in text:
            score = max(score, 10)
        if label and label in text:
            score = max(score, 8)
        if catalog_prompt:
            if catalog_prompt.startswith(text) or text.startswith(catalog_prompt):
                score = max(score, 9)
            elif catalog_prompt[:40] in text or text[:40] in catalog_prompt:
                score = max(score, 6)
            overlap = max(
                _word_overlap(text, catalog_prompt),
                _word_overlap(text, label),
                _word_overlap(text, pid.replace("_", " ")),
            )
            if overlap >= 3:
                score = max(score, overlap)
        if score > best_score:
            best_score = score
            best_id = pid
    return best_id


def attach_context_from_run(
    rows: list[dict[str, Any]], repo_root: Path | None = None
) -> dict[str, str]:
    business_prompt = ""
    workflow_profile = ""
    for row in rows:
        if row.get("event_type") != "run.created":
            continue
        meta = row.get("metadata") or {}
        workflow_profile = str(meta.get("workflow_profile") or "")
        req = meta.get("requirements") or {}
        if isinstance(req, dict):
            business_prompt = str(req.get("business_prompt") or "").strip()
        break
    ctx: dict[str, str] = {}
    if workflow_profile:
        ctx["workflow_profile"] = workflow_profile
    if business_prompt:
        ctx["business_prompt"] = business_prompt
    prompt_id = match_prompt_id(business_prompt, repo_root)
    if prompt_id:
        ctx["prompt_id"] = prompt_id
    return ctx
