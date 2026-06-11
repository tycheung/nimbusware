from __future__ import annotations

from fastapi.routing import APIRoute

from nimbusware_api.facade import build_v1_router


def _route_paths(router) -> set[str]:
    paths: set[str] = set()
    for route in router.routes:
        if isinstance(route, APIRoute):
            paths.add(route.path)
    return paths


def test_build_v1_router_includes_core_routes() -> None:
    paths = _route_paths(build_v1_router())
    assert "/runs" in paths
    assert "/runs/{run_id}/timeline" in paths
    assert "/preflight-history" in paths
    assert "/platform/edition" in paths
    assert "/platform/ollama/models" in paths
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
    assert "/enterprise/fleet-ollama-sli/status" in paths


def test_build_v1_router_includes_runs_subpackage() -> None:
    from nimbusware_api.routes.runs import build_runs_router

    paths = _route_paths(build_runs_router())
    assert "/runs" in paths
    assert "/runs/{run_id}/lifecycle/slice" in paths


def test_enterprise_package_exports_build_router() -> None:
    from nimbusware_api.routes.enterprise import build_enterprise_router

    paths = _route_paths(build_enterprise_router())
    assert "/enterprise/status" in paths
    assert "/enterprise/iam/me" in paths
