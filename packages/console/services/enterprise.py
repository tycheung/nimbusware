from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from client.http import get_json
from iam.constants import API_KEY_HEADER


def build_enterprise_headers(api_key: str | None) -> dict[str, str]:
    if api_key is None or not str(api_key).strip():
        return {}
    return {API_KEY_HEADER: str(api_key).strip()}


def _enterprise_get(
    path: str,
    *,
    api_key: str | None,
    params: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    suffix = path if path.startswith("/") else f"/{path}"
    return get_json(
        suffix,
        params=params,
        headers=build_enterprise_headers(api_key),
        timeout=timeout,
    )


def fetch_platform_edition(*, timeout: float = 15.0) -> dict[str, Any]:
    return get_json("/platform/edition", timeout=timeout)


def fetch_iam_me(*, api_key: str, timeout: float = 15.0) -> dict[str, Any]:
    return _enterprise_get("/enterprise/iam/me", api_key=api_key, timeout=timeout)


def fetch_tenants(*, api_key: str, timeout: float = 15.0) -> dict[str, Any]:
    return _enterprise_get("/enterprise/tenants", api_key=api_key, timeout=timeout)


def fetch_fleet_memory_status(
    *,
    api_key: str,
    timeout: float = 30.0,
) -> dict[str, Any]:
    return _enterprise_get(
        "/enterprise/fleet-memory/status",
        api_key=api_key,
        timeout=timeout,
    )


def fetch_fleet_preflight_aggregate(
    *,
    api_key: str,
    limit: int = 10,
    timeout: float = 30.0,
) -> dict[str, Any]:
    return _enterprise_get(
        "/enterprise/fleet-ollama-sli/preflight-aggregate",
        api_key=api_key,
        params={"limit": max(1, min(50, int(limit))), "include_metrics_export": 1},
        timeout=timeout,
    )


def fetch_fleet_worker_health(
    *,
    api_key: str,
    timeout: float = 30.0,
) -> dict[str, Any]:
    return _enterprise_get(
        "/enterprise/fleet-worker/health",
        api_key=api_key,
        timeout=timeout,
    )


def fetch_platform_hardware_fleet(*, timeout: float = 30.0) -> dict[str, Any]:
    return get_json("/platform/hardware/fleet", timeout=timeout)


def fetch_fleet_analytics_compare(
    *,
    api_key: str,
    tenant_a: str,
    tenant_b: str,
    run_limit: int = 100,
    timeout: float = 30.0,
) -> dict[str, Any]:
    return _enterprise_get(
        "/enterprise/fleet/analytics/compare",
        api_key=api_key,
        params={
            "tenant_a": tenant_a,
            "tenant_b": tenant_b,
            "run_limit": max(1, min(500, int(run_limit))),
        },
        timeout=timeout,
    )


def fetch_fleet_critic_reliability(
    *,
    api_key: str,
    tenant_id: str,
    run_limit: int = 100,
    timeout: float = 30.0,
) -> dict[str, Any]:
    return _enterprise_get(
        "/enterprise/fleet/critic-reliability",
        api_key=api_key,
        params={
            "tenant_id": tenant_id,
            "run_limit": max(1, min(500, int(run_limit))),
        },
        timeout=timeout,
    )


def is_enterprise_edition_manifest(manifest: Mapping[str, Any] | None) -> bool:
    if not isinstance(manifest, Mapping):
        return False
    return str(manifest.get("edition", "")).strip().lower() == "enterprise"


def enterprise_console_feature_enabled(manifest: Mapping[str, Any] | None) -> bool:
    if manifest is None or not is_enterprise_edition_manifest(manifest):
        return False
    features = manifest.get("features")
    if not isinstance(features, Mapping):
        return False
    block = features.get("enterprise_console")
    if not isinstance(block, Mapping):
        return False
    return str(block.get("status", "")).strip().lower() == "enabled"
