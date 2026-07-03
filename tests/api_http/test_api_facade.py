from __future__ import annotations

from typing import Any

from fastapi.routing import APIRoute

from api.facade import build_v1_router


def _iter_api_routes(router: Any):
    for route in router.routes:
        if isinstance(route, APIRoute):
            yield route
        elif hasattr(route, "original_router"):
            yield from _iter_api_routes(route.original_router)
        elif hasattr(route, "routes"):
            yield from _iter_api_routes(route)


def _route_paths(router) -> set[str]:
    return {route.path for route in _iter_api_routes(router)}


def test_build_v1_router_includes_core_routes() -> None:
    paths = _route_paths(build_v1_router())
    assert "/runs" in paths
    assert "/runs/{run_id}/timeline" in paths
    assert "/preflight-history" in paths
    assert "/platform/edition" in paths
    assert "/platform/ollama/models" in paths
    assert "/platform/provider-presets" in paths
    assert "/platform/provider-connections" in paths
    assert "/platform/provider-subscriptions/oauth/status" in paths
    assert "/platform/provider-subscriptions/{provider_id}/oauth/authorize" in paths
    assert "/platform/ollama/bootstrap" in paths
    assert "/platform/model-bindings/preflight" in paths
    assert "/platform/model-bindings/defaults" in paths
    assert "/platform/model-bindings/roles" in paths
    assert "/compute/nodes/register" in paths
    assert "/sessions/{session_id}/compute/opt-in" in paths
    assert "/admin/ollama/user-policy" in paths


def test_build_v1_router_includes_enterprise_routes() -> None:
    paths = _route_paths(build_v1_router())
    assert "/enterprise/status" in paths
    assert "/enterprise/health" in paths
    assert "/enterprise/iam/me" in paths
    assert "/enterprise/fleet-memory/status" in paths
    assert "/enterprise/config-notify/status" in paths
    assert "/enterprise/scraper-artifacts/storage" in paths
    assert "/enterprise/fleet-worker/health" in paths
    assert "/enterprise/fleet-mesh/status" in paths
    assert "/enterprise/fleet-ollama-sli/status" in paths


def test_build_v1_router_includes_runs_subpackage() -> None:
    from api.routes.runs import build_runs_router

    paths = _route_paths(build_runs_router())
    assert "/runs" in paths
    assert "/runs/{run_id}/lifecycle/slice" in paths


def test_enterprise_package_exports_build_router() -> None:
    from api.routes.enterprise import build_enterprise_router

    paths = _route_paths(build_enterprise_router())
    assert "/enterprise/status" in paths
    assert "/enterprise/iam/me" in paths
