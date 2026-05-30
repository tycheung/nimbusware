from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from nimbusware_client.http import get_json
from nimbusware_console.preflight_cross_run_display import (
    preflight_history_response_sli_caption,
)
from nimbusware_iam.constants import API_KEY_HEADER

SS_API_KEY = "hermes_enterprise_api_key"
SS_TENANT_KEYS = "hermes_enterprise_tenant_api_keys"
SS_SELECTED_TENANT = "hermes_enterprise_selected_tenant_slug"
SS_IAM_ME = "hermes_enterprise_iam_me"
SS_EDITION_MANIFEST = "hermes_enterprise_edition_manifest"


def build_enterprise_headers(api_key: str | None) -> dict[str, str]:
    if api_key is None or not str(api_key).strip():
        return {}
    return {API_KEY_HEADER: str(api_key).strip()}


def is_enterprise_edition_manifest(manifest: Mapping[str, Any] | None) -> bool:
    if not isinstance(manifest, Mapping):
        return False
    return str(manifest.get("edition", "")).strip().lower() == "enterprise"


def enterprise_console_feature_enabled(manifest: Mapping[str, Any] | None) -> bool:
    if not is_enterprise_edition_manifest(manifest):
        return False
    features = manifest.get("features")
    if not isinstance(features, Mapping):
        return False
    block = features.get("enterprise_console")
    if not isinstance(block, Mapping):
        return False
    return str(block.get("status", "")).strip().lower() == "enabled"


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


def tenant_select_options(tenants_body: Mapping[str, Any] | None) -> list[tuple[str, str]]:
    if not isinstance(tenants_body, Mapping):
        return []
    raw = tenants_body.get("tenants")
    if not isinstance(raw, list):
        return []
    out: list[tuple[str, str]] = []
    for row in raw:
        if not isinstance(row, Mapping):
            continue
        slug = row.get("slug")
        if not isinstance(slug, str) or not slug.strip():
            continue
        display = row.get("display_name")
        label = slug.strip()
        if isinstance(display, str) and display.strip():
            label = f"{slug.strip()} — {display.strip()}"
        out.append((slug.strip(), label))
    out.sort(key=lambda x: x[0])
    return out


def resolve_active_api_key(
    *,
    primary_key: str | None,
    tenant_keys: Mapping[str, str] | None,
    selected_tenant_slug: str | None,
) -> str | None:
    if selected_tenant_slug and tenant_keys:
        mapped = tenant_keys.get(selected_tenant_slug)
        if isinstance(mapped, str) and mapped.strip():
            return mapped.strip()
    if primary_key and str(primary_key).strip():
        return str(primary_key).strip()
    return None


def register_tenant_api_key(
    tenant_keys: dict[str, str],
    *,
    tenant_slug: str,
    api_key: str,
) -> dict[str, str]:
    out = dict(tenant_keys)
    out[tenant_slug.strip()] = api_key.strip()
    return out


def fleet_memory_status_table_rows(body: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(body, Mapping):
        return []
    remote = body.get("remote") if isinstance(body.get("remote"), Mapping) else {}
    return [
        {"field": "tenant_id", "value": body.get("tenant_id")},
        {"field": "org_scope_hash", "value": body.get("org_scope_hash")},
        {"field": "local_generation_id", "value": body.get("local_generation_id")},
        {"field": "local_chunk_count", "value": body.get("local_chunk_count")},
        {"field": "fleet_memory_enabled", "value": body.get("fleet_memory_enabled")},
        {"field": "remote_configured", "value": remote.get("configured")},
        {"field": "remote_generation_id", "value": remote.get("generation_id")},
    ]


def fleet_worker_health_caption(body: Mapping[str, Any] | None) -> str | None:
    if not isinstance(body, Mapping):
        return None
    backpressure = body.get("backpressure")
    ok = body.get("ok")
    parts: list[str] = []
    if isinstance(ok, bool):
        parts.append(f"ok={'yes' if ok else 'no'}")
    if isinstance(backpressure, str) and backpressure.strip():
        parts.append(f"backpressure={backpressure.strip()}")
    metrics = body.get("metrics")
    if isinstance(metrics, Mapping):
        queue = metrics.get("queue")
        if isinstance(queue, Mapping):
            pending = queue.get("pending")
            inflight = queue.get("in_flight")
            if pending is not None:
                parts.append(f"pending={pending}")
            if inflight is not None:
                parts.append(f"in_flight={inflight}")
    if not parts:
        return None
    return "Fleet worker: " + ", ".join(parts) + "."


def fleet_sli_aggregate_caption(body: Mapping[str, Any] | None) -> str | None:
    if not isinstance(body, Mapping):
        return None
    fleet_sli = body.get("fleet_sli")
    if isinstance(fleet_sli, Mapping):
        combined = fleet_sli.get("combined_max_p95_latency_ms")
        sustained = fleet_sli.get("sustained_p95_latency_ms")
        present = fleet_sli.get("sustained_export_present")
        parts: list[str] = []
        if isinstance(present, bool):
            parts.append(f"sustained_export={'yes' if present else 'no'}")
        if isinstance(sustained, int) and not isinstance(sustained, bool):
            parts.append(f"sustained_p95_ms={sustained}")
        if isinstance(combined, int) and not isinstance(combined, bool):
            parts.append(f"combined_max_p95_ms={combined}")
        if parts:
            base = "Fleet Ollama SLI: " + ", ".join(parts) + "."
        else:
            base = None
    else:
        base = None
    history = body.get("preflight_history")
    hist_cap = (
        preflight_history_response_sli_caption(history)
        if isinstance(history, Mapping)
        else None
    )
    if base and hist_cap:
        return f"{base} {hist_cap}"
    return base or hist_cap


def fleet_dashboard_export_json(
    *,
    memory: Mapping[str, Any] | None,
    preflight_aggregate: Mapping[str, Any] | None,
    worker: Mapping[str, Any] | None,
) -> str:
    payload = {
        "fleet_memory": dict(memory) if isinstance(memory, Mapping) else None,
        "preflight_aggregate": (
            dict(preflight_aggregate) if isinstance(preflight_aggregate, Mapping) else None
        ),
        "fleet_worker": dict(worker) if isinstance(worker, Mapping) else None,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def fleet_dashboard_export_filename_slug() -> str:
    return "enterprise_fleet_dashboard"
