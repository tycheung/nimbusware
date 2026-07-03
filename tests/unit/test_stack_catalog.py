from __future__ import annotations

from pathlib import Path

from env import find_repo_root
from orchestrator.stack_catalog import (
    load_stack_catalog,
    resolve_manifest_stacks,
    stack_for_surface,
    writer_role_for_surface,
)


def test_load_stack_catalog_has_core_stacks() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    catalog = load_stack_catalog(repo)
    assert "fastapi_python" in catalog
    assert "react_vite" in catalog
    assert "expo" in catalog
    assert catalog["fastapi_python"].surface == "api"
    assert catalog["react_vite"].surface == "web"
    assert catalog["expo"].surface == "mobile"
    assert catalog["react_vite"].max_files == 4
    assert catalog["fastapi_python"].max_loc == 200


def test_resolve_manifest_stacks() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    manifest = {
        "surfaces": ["api", "web"],
        "stacks": {"api": "fastapi_python", "web": "react_vite"},
    }
    resolved = resolve_manifest_stacks(manifest, repo_root=repo)
    assert set(resolved) == {"api", "web"}
    assert resolved["web"].launch_framework_id == "react_vite"


def test_stack_for_surface() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    manifest = {"stacks": {"api": "node_express"}}
    stack = stack_for_surface(manifest, "api", repo_root=repo)
    assert stack is not None
    assert stack.stack_id == "node_express"


def test_writer_role_for_surface() -> None:
    assert writer_role_for_surface("web") == "frontend_writer"
    assert writer_role_for_surface("mobile") == "frontend_writer"
    assert writer_role_for_surface("api") == "backend_writer"
    assert writer_role_for_surface("deploy") == "infra_writer"
    assert writer_role_for_surface("infra") == "integration_adapter_writer"
