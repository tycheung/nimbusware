from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from agent_core.coercion import is_strict_int
from console.preflight_cross_run_display import (
    preflight_history_response_sli_caption,
)
from console.services import enterprise as enterprise_svc

SS_API_KEY = "nimbusware_enterprise_api_key"
SS_TENANT_KEYS = "nimbusware_enterprise_tenant_api_keys"
SS_SELECTED_TENANT = "nimbusware_enterprise_selected_tenant_slug"
SS_IAM_ME = "nimbusware_enterprise_iam_me"
SS_EDITION_MANIFEST = "nimbusware_enterprise_edition_manifest"


build_enterprise_headers = enterprise_svc.build_enterprise_headers
is_enterprise_edition_manifest = enterprise_svc.is_enterprise_edition_manifest
enterprise_console_feature_enabled = enterprise_svc.enterprise_console_feature_enabled
fetch_platform_edition = enterprise_svc.fetch_platform_edition
fetch_iam_me = enterprise_svc.fetch_iam_me
fetch_tenants = enterprise_svc.fetch_tenants
fetch_fleet_memory_status = enterprise_svc.fetch_fleet_memory_status
fetch_fleet_preflight_aggregate = enterprise_svc.fetch_fleet_preflight_aggregate
fetch_fleet_worker_health = enterprise_svc.fetch_fleet_worker_health
fetch_fleet_critic_reliability = enterprise_svc.fetch_fleet_critic_reliability
fetch_platform_hardware_fleet = enterprise_svc.fetch_platform_hardware_fleet


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
        if is_strict_int(sustained):
            parts.append(f"sustained_p95_ms={sustained}")
        if is_strict_int(combined):
            parts.append(f"combined_max_p95_ms={combined}")
        if parts:
            base = "Fleet Ollama SLI: " + ", ".join(parts) + "."
        else:
            base = None
    else:
        base = None
    history = body.get("preflight_history")
    hist_cap = (
        preflight_history_response_sli_caption(history) if isinstance(history, Mapping) else None
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


def fleet_hardware_tier_table_rows(body: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(body, Mapping):
        return []
    hosts = body.get("hosts")
    if not isinstance(hosts, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in hosts:
        if not isinstance(item, Mapping):
            continue
        err_list = item.get("errors")
        err_text = ", ".join(str(e) for e in err_list[:3]) if isinstance(err_list, list) else ""
        rows.append(
            {
                "host": item.get("host", ""),
                "tier": item.get("tier", ""),
                "ram_total_gb": item.get("ram_total_gb"),
                "ram_available_gb": item.get("ram_available_gb"),
                "cpu_count": item.get("cpu_count"),
                "gpu_count": item.get("gpu_count"),
                "platform": item.get("platform", ""),
                "errors": err_text,
            },
        )
    rows.sort(key=lambda r: (str(r.get("tier")), str(r.get("host"))))
    return rows


def fleet_compare_caption(body: Mapping[str, Any] | None) -> str:
    if not isinstance(body, Mapping):
        return (
            "Cross-tenant gate comparison. Ollama SLI in each column is a fleet-wide snapshot "
            "(not per-tenant)."
        )
    comp = body.get("comparison")
    if not isinstance(comp, Mapping):
        return (
            "Cross-tenant gate comparison. Ollama SLI in each column is a fleet-wide snapshot "
            "(not per-tenant)."
        )
    return (
        "Cross-tenant gate comparison. Ollama SLI columns reflect fleet-wide snapshot "
        f"(pass delta {comp.get('gate_pass_delta', 0)}, fail delta {comp.get('gate_fail_delta', 0)})."
    )


def fleet_compare_table_rows(body: Mapping[str, Any] | None) -> list[dict[str, str]]:
    if not isinstance(body, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for label, key in (("Tenant A", "tenant_a"), ("Tenant B", "tenant_b")):
        block = body.get(key)
        if not isinstance(block, Mapping):
            continue
        gates = block.get("gate_metrics")
        if not isinstance(gates, Mapping):
            gates = {}
        sli = block.get("ollama_sli")
        p95 = ""
        if isinstance(sli, Mapping) and sli.get("sustained_p95_latency_ms") is not None:
            p95 = str(sli.get("sustained_p95_latency_ms"))
        rows.append(
            {
                "tenant": label,
                "tenant_id": str(block.get("tenant_id", "")),
                "runs_scanned": str(block.get("runs_scanned", 0)),
                "gates_passed": str(gates.get("slice_gates_passed", 0)),
                "gates_failed": str(gates.get("slice_gates_failed", 0)),
                "ollama_p95_ms": p95 or "fleet snapshot",
            },
        )
    comp = body.get("comparison")
    if isinstance(comp, Mapping):
        rows.append(
            {
                "tenant": "Delta (B − A)",
                "tenant_id": "",
                "runs_scanned": "—",
                "gates_passed": str(comp.get("gate_pass_delta", 0)),
                "gates_failed": str(comp.get("gate_fail_delta", 0)),
                "ollama_p95_ms": "—",
            },
        )
    return rows


def fleet_compare_csv(rows: list[dict[str, str]]) -> str:
    """Serialize fleet compare table rows as CSV for procurement exports."""
    if not rows:
        return "tenant,tenant_id,runs_scanned,gates_passed,gates_failed,ollama_p95_ms\n"
    fieldnames = [
        "tenant",
        "tenant_id",
        "runs_scanned",
        "gates_passed",
        "gates_failed",
        "ollama_p95_ms",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in fieldnames})
    return buf.getvalue()


def archetype_fit_dashboard_rows(repo_root: Path | None = None) -> list[dict[str, str]]:
    from env import find_repo_root

    try:
        body = json.loads(
            (
                (repo_root or find_repo_root()) / "benchmarks" / "latest_archetype_metrics.json"
            ).read_text(
                encoding="utf-8",
            ),
        )
        archetypes = body.get("archetypes") if isinstance(body, dict) else {}
    except (OSError, json.JSONDecodeError, TypeError):
        return []
    if not isinstance(archetypes, dict):
        return []
    out: list[dict[str, str]] = []
    for name in ("safe_coding", "engineer", "enterprise"):
        row = archetypes.get(name)
        if not isinstance(row, dict):
            continue
        score = row.get("fit_score")
        out.append(
            {
                "archetype": name.replace("_", " ").title(),
                "fit_score": f"{float(score):.0%}" if isinstance(score, (int, float)) else "—",
                "meets_target": "yes" if row.get("meets_target") else "no",
            },
        )
    return out
