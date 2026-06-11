from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import httpx
import yaml

from agent_core.mapping import mapping_or_empty
from nimbusware_orchestrator.role_telemetry import aggregate_role_telemetry_rows

ProviderKind = Literal["local", "cloud"]

_DEFAULT_COST_PER_1K_TOKENS_USD = 0.003


def load_routing_presets(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "configs" / "routing_presets.yaml"
    if not path.is_file():
        return {"version": 1, "presets": {}}
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else {"version": 1, "presets": {}}


def list_routing_preset_summaries(repo_root: Path) -> list[dict[str, Any]]:
    doc = load_routing_presets(repo_root)
    presets = mapping_or_empty(doc.get("presets"))
    out: list[dict[str, Any]] = []
    for preset_id, raw in sorted(presets.items()):
        block = mapping_or_empty(raw)
        out.append(
            {
                "id": preset_id,
                "label": str(block.get("label") or preset_id),
                "description": str(block.get("description") or ""),
                "stage_providers": dict(mapping_or_empty(block.get("stage_providers"))),
                "cloud_enabled": bool(mapping_or_empty(block.get("cloud_runtime")).get("enabled")),
            },
        )
    return out


def apply_routing_preset(repo_root: Path, preset_id: str) -> dict[str, Any]:
    doc = load_routing_presets(repo_root)
    presets = mapping_or_empty(doc.get("presets"))
    block = mapping_or_empty(presets.get(preset_id))
    if not block:
        raise KeyError(preset_id)
    routing_path = repo_root / "configs" / "model-routing.yaml"
    routing = _load_routing_yaml(routing_path)
    cloud_cfg = mapping_or_empty(block.get("cloud_runtime"))
    stage_providers = mapping_or_empty(block.get("stage_providers"))
    routing["cloud_runtime"] = {
        "enabled": bool(cloud_cfg.get("enabled")),
        "provider": str(cloud_cfg.get("provider") or "openai_compatible"),
        "base_url": str(cloud_cfg.get("base_url") or "https://api.openai.com/v1"),
        "api_key_env": str(cloud_cfg.get("api_key_env") or "OPENAI_API_KEY"),
        "model_id": str(cloud_cfg.get("model_id") or "gpt-4o-mini"),
        "health_path": str(cloud_cfg.get("health_path") or "/models"),
    }
    routing["stage_providers"] = dict(stage_providers)
    routing["routing_preset_id"] = preset_id
    _write_routing_yaml(routing_path, routing)
    return {
        "preset_id": preset_id,
        "label": str(block.get("label") or preset_id),
        "cloud_enabled": bool(cloud_cfg.get("enabled")),
        "stage_providers": dict(stage_providers),
        "materialize_hint": "Restart API or run nimbusware-config materialize to reload routing",
    }


def resolve_stage_provider(routing: dict[str, Any], stage_name: str) -> ProviderKind:
    providers = mapping_or_empty(routing.get("stage_providers"))
    raw = providers.get(stage_name)
    if raw is None:
        return "local"
    token = str(raw).strip().lower()
    if token == "cloud" and bool(mapping_or_empty(routing.get("cloud_runtime")).get("enabled")):
        return "cloud"
    return "local"


def probe_cloud_runtime(routing: dict[str, Any], *, timeout_seconds: float = 10.0) -> dict[str, Any]:
    cloud = mapping_or_empty(routing.get("cloud_runtime"))
    if not cloud.get("enabled"):
        return {"enabled": False, "reachable": None, "message": "cloud runtime disabled"}
    base_url = str(cloud.get("base_url") or "").strip().rstrip("/")
    health_path = str(cloud.get("health_path") or "/models").lstrip("/")
    api_key_env = str(cloud.get("api_key_env") or "OPENAI_API_KEY")
    api_key = os.environ.get(api_key_env, "").strip()
    if not api_key:
        return {
            "enabled": True,
            "reachable": False,
            "message": f"missing API key env {api_key_env}",
            "api_key_env": api_key_env,
        }
    url = f"{base_url}/{health_path}"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = httpx.get(url, headers=headers, timeout=timeout_seconds)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        return {
            "enabled": True,
            "reachable": False,
            "message": str(exc),
            "base_url": base_url,
            "api_key_env": api_key_env,
        }
    return {
        "enabled": True,
        "reachable": True,
        "message": "cloud runtime reachable",
        "base_url": base_url,
        "model_id": cloud.get("model_id"),
        "api_key_env": api_key_env,
    }


def summarize_run_role_cost(
    rows: list[dict[str, Any]],
    *,
    routing: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    doc = aggregate_role_telemetry_rows(rows)
    roles = mapping_or_empty(doc.get("roles"))
    if not roles:
        return None
    prompt_total = 0
    completion_total = 0
    latency_samples: list[int] = []
    for role_doc in roles.values():
        hints = mapping_or_empty(role_doc.get("token_hints"))
        prompt_total += int(hints.get("prompt_tokens_total") or 0)
        completion_total += int(hints.get("completion_tokens_total") or 0)
        lat = mapping_or_empty(role_doc.get("inference_latency_ms"))
        p95 = lat.get("p95")
        if isinstance(p95, int):
            latency_samples.append(p95)
    if not prompt_total and not completion_total and not latency_samples:
        return None
    cloud = mapping_or_empty((routing or {}).get("cloud_runtime"))
    cloud_enabled = bool(cloud.get("enabled"))
    token_total = prompt_total + completion_total
    cost_usd = None
    if cloud_enabled and token_total:
        rate = float(cloud.get("cost_per_1k_tokens_usd") or _DEFAULT_COST_PER_1K_TOKENS_USD)
        cost_usd = round((token_total / 1000.0) * rate, 4)
    summary: dict[str, Any] = {
        "prompt_tokens": prompt_total,
        "completion_tokens": completion_total,
        "token_total": token_total,
        "cloud_enabled": cloud_enabled,
    }
    if latency_samples:
        summary["inference_p95_ms"] = max(latency_samples)
    if cost_usd is not None:
        summary["estimated_cost_usd"] = cost_usd
    preset = (routing or {}).get("routing_preset_id")
    if isinstance(preset, str) and preset.strip():
        summary["routing_preset_id"] = preset.strip()
    return summary


def _load_routing_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"version": 1, "models": {}}
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else {"version": 1, "models": {}}


def _write_routing_yaml(path: Path, content: dict[str, Any]) -> None:
    path.write_text(yaml.dump(content, sort_keys=False), encoding="utf-8")
