from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from nimbusware_env import find_repo_root


def factory_flows_root(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "factory" / "flows"


def load_factory_flow_catalog(repo_root: Path | None = None) -> dict[str, Any]:
    path = factory_flows_root(repo_root) / "catalog.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def list_factory_flow_ids(repo_root: Path | None = None) -> tuple[str, ...]:
    doc = load_factory_flow_catalog(repo_root)
    return tuple(str(entry["id"]) for entry in doc.get("flows") or [] if entry.get("id"))


def load_factory_flow(flow_id: str, repo_root: Path | None = None) -> dict[str, Any]:
    root = factory_flows_root(repo_root)
    catalog = load_factory_flow_catalog(repo_root)
    rel = ""
    for entry in catalog.get("flows") or []:
        if str(entry.get("id") or "").strip() == flow_id:
            rel = str(entry.get("path") or "").strip()
            break
    if not rel:
        raise KeyError(f"unknown factory flow id: {flow_id}")
    path = root / rel
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not data.get("id"):
        data["id"] = flow_id
    return data


def match_factory_flow_id(
    business_prompt: str,
    *,
    prompt_id: str | None = None,
    repo_root: Path | None = None,
) -> str | None:
    if prompt_id:
        catalog = load_factory_flow_catalog(repo_root)
        for entry in catalog.get("flows") or []:
            if str(entry.get("prompt_id") or "") == prompt_id:
                return str(entry.get("id") or "") or None
    text = business_prompt.strip().lower()
    if not text:
        return None
    for fid in list_factory_flow_ids(repo_root):
        if fid.replace("_", " ") in text or fid in text:
            return fid
    return None
