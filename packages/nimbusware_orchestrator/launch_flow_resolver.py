"""Resolve HTTP, UI, and slice.e2e flows for PUT launch testing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.put_e2e_runner import match_factory_flow_id
from nimbusware_orchestrator.ui_flow_dsl import UiFlowDefinition, load_ui_flow


@dataclass(frozen=True)
class ResolvedLaunchFlows:
    http_flow_id: str | None = None
    ui_flow_id: str | None = None
    slice_e2e_command: str | None = None
    ui_flow: UiFlowDefinition | None = None
    source: str = "default"


def ui_flows_root(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "factory" / "ui_flows"


def workspace_ui_flows_dir(workspace: Path) -> Path:
    return workspace.resolve() / ".nimbusware" / "dev_env" / "ui_flows"


def load_ui_flow_catalog(repo_root: Path | None = None) -> dict[str, Any]:
    path = ui_flows_root(repo_root) / "catalog.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def list_ui_flow_ids(repo_root: Path | None = None) -> tuple[str, ...]:
    doc = load_ui_flow_catalog(repo_root)
    return tuple(str(entry["id"]) for entry in doc.get("flows") or [] if entry.get("id"))


def load_catalog_ui_flow(flow_id: str, repo_root: Path | None = None) -> UiFlowDefinition:
    root = ui_flows_root(repo_root)
    catalog = load_ui_flow_catalog(repo_root)
    rel = ""
    for entry in catalog.get("flows") or []:
        if str(entry.get("id") or "").strip() == flow_id:
            rel = str(entry.get("path") or "").strip()
            break
    if not rel:
        raise KeyError(f"unknown ui flow id: {flow_id}")
    path = root / rel
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return load_ui_flow(flow_id, raw)


def load_workspace_ui_flow(workspace: Path, flow_id: str) -> UiFlowDefinition | None:
    path = workspace_ui_flows_dir(workspace) / f"{flow_id}.yaml"
    if not path.is_file():
        return None
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return load_ui_flow(flow_id, raw)


def match_ui_flow_id(
    business_prompt: str,
    *,
    prompt_id: str | None = None,
    http_flow_id: str | None = None,
    repo_root: Path | None = None,
) -> str | None:
    if prompt_id:
        catalog = load_ui_flow_catalog(repo_root)
        for entry in catalog.get("flows") or []:
            if str(entry.get("prompt_id") or "") == prompt_id:
                return str(entry.get("id") or "") or None
    if http_flow_id:
        companion = f"{http_flow_id}_ui"
        if companion in list_ui_flow_ids(repo_root):
            return companion
    text = business_prompt.strip().lower()
    if not text:
        return None
    for fid in list_ui_flow_ids(repo_root):
        if fid.replace("_", " ") in text or fid in text:
            return fid
    return None


def resolve_ui_flow(
    workspace: Path,
    *,
    flow_id: str | None = None,
    business_prompt: str = "",
    prompt_id: str | None = None,
    http_flow_id: str | None = None,
    repo_root: Path | None = None,
) -> tuple[UiFlowDefinition | None, str]:
    fid = flow_id
    if not fid:
        ws_flow = _first_workspace_ui_flow(workspace)
        if ws_flow:
            return ws_flow, "workspace"
        fid = match_ui_flow_id(
            business_prompt,
            prompt_id=prompt_id,
            http_flow_id=http_flow_id,
            repo_root=repo_root,
        )
        if fid:
            try:
                return load_catalog_ui_flow(fid, repo_root), "catalog"
            except KeyError:
                pass
        return None, "none"
    ws = load_workspace_ui_flow(workspace, fid)
    if ws is not None:
        return ws, "workspace"
    try:
        return load_catalog_ui_flow(fid, repo_root), "catalog"
    except KeyError:
        return None, "none"


def _first_workspace_ui_flow(workspace: Path) -> UiFlowDefinition | None:
    flows_dir = workspace_ui_flows_dir(workspace)
    if not flows_dir.is_dir():
        return None
    for path in sorted(flows_dir.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return load_ui_flow(path.stem, raw)
    return None


def _prompt_from_rows(rows: list[dict[str, Any]]) -> tuple[str, str | None]:
    prompt = ""
    prompt_id: str | None = None
    for row in rows:
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        if not prompt and meta.get("business_prompt"):
            prompt = str(meta["business_prompt"])
        if not prompt_id and meta.get("prompt_id"):
            prompt_id = str(meta["prompt_id"])
    return prompt, prompt_id


def resolve_launch_flows(
    rows: list[dict[str, Any]],
    workspace: Path,
    *,
    ui_flow_id: str | None = None,
    repo_root: Path | None = None,
) -> ResolvedLaunchFlows:
    prompt, prompt_id = _prompt_from_rows(rows)
    http_flow_id = match_factory_flow_id(prompt, prompt_id=prompt_id, repo_root=repo_root)
    ui_flow, source = resolve_ui_flow(
        workspace,
        flow_id=ui_flow_id,
        business_prompt=prompt,
        prompt_id=prompt_id,
        http_flow_id=http_flow_id,
        repo_root=repo_root,
    )
    slice_cmd = _slice_e2e_command_from_rows(rows)
    return ResolvedLaunchFlows(
        http_flow_id=http_flow_id,
        ui_flow_id=ui_flow.flow_id if ui_flow else None,
        slice_e2e_command=slice_cmd,
        ui_flow=ui_flow,
        source=source,
    )


def _slice_e2e_command_from_rows(rows: list[dict[str, Any]]) -> str | None:
    for row in reversed(rows):
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        cmd = meta.get("slice_e2e_command")
        if cmd:
            return str(cmd)
    return None
