"""Runs router facade — route surface and import shim contracts (Phase 3)."""

from __future__ import annotations
from nimbusware_env import find_repo_root

import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import nimbusware_api.routes.runs as runs_module
from nimbusware_api.app import app
from nimbusware_api.facade import build_v1_router

os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(find_repo_root(start=Path(__file__).resolve().parents[1])))

EXPECTED_RUN_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/runs"),
        ("POST", "/runs"),
        ("GET", "/runs/{run_id}"),
        ("GET", "/runs/{run_id}/timeline"),
        ("GET", "/runs/{run_id}/findings"),
        ("POST", "/runs/{run_id}/lifecycle/start"),
        ("POST", "/runs/{run_id}/lifecycle/plan"),
        ("POST", "/runs/{run_id}/lifecycle/verify"),
        ("POST", "/runs/{run_id}/lifecycle/slice"),
    },
)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def _route_methods(router: Any) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for route in router.routes:
        if isinstance(route, APIRoute):
            for method in route.methods:
                out.add((method.upper(), route.path))
    return out


def _openapi_run_paths(spec: dict[str, Any]) -> set[tuple[str, str]]:
    paths = spec.get("paths", {})
    out: set[tuple[str, str]] = set()
    for path, ops in paths.items():
        if not path.startswith("/v1/runs"):
            continue
        rel = path.removeprefix("/v1")
        for method in ops:
            if method in ("get", "post", "put", "patch", "delete"):
                out.add((method.upper(), rel))
    return out


def test_runs_module_exports_router_and_constants() -> None:
    assert hasattr(runs_module, "router")
    assert runs_module.INCLUDE_SUMMARY_MAX_LIMIT == 20
    assert hasattr(runs_module, "CreateRunBody")


def test_runs_router_has_expected_route_surface() -> None:
    assert _route_methods(runs_module.router) == EXPECTED_RUN_ROUTES


def test_build_runs_router_matches_module_router() -> None:
    build = getattr(runs_module, "build_runs_router", None)
    if build is None:
        pytest.skip("build_runs_router not yet split from monolithic runs.py")
    assert _route_methods(build()) == _route_methods(runs_module.router)


def test_runs_sub_routers_cover_full_surface() -> None:
    sub_names = ("list_router", "create_router", "detail_router", "lifecycle_router")
    if not all(hasattr(runs_module, name) for name in sub_names):
        pytest.skip("runs sub-routers not yet extracted")
    combined: set[tuple[str, str]] = set()
    for name in sub_names:
        combined |= _route_methods(getattr(runs_module, name))
    assert combined == EXPECTED_RUN_ROUTES


def test_v1_facade_includes_runs_routes() -> None:
    facade_runs = {
        pair
        for pair in _route_methods(build_v1_router())
        if pair in EXPECTED_RUN_ROUTES
    }
    assert facade_runs == EXPECTED_RUN_ROUTES


def test_openapi_runs_paths_match_router(client: Any) -> None:
    """OpenAPI paths for runs handlers must match the runs router (no drift)."""
    spec = client.app.openapi()
    openapi_runs = _openapi_run_paths(spec)
    assert EXPECTED_RUN_ROUTES <= openapi_runs
    assert _route_methods(runs_module.router) <= openapi_runs


def test_runs_router_tags(client: Any) -> None:
    spec = client.app.openapi()
    for method, rel_path in EXPECTED_RUN_ROUTES:
        path = f"/v1{rel_path}"
        op = spec["paths"][path][method.lower()]
        assert op.get("tags") == ["runs"]
