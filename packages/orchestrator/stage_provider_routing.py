from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import httpx

from agent_core.mapping import mapping_or_empty
from env.env_flags import env_str
from orchestrator.routing.presets import load_model_routing_yaml
from orchestrator.llm.prompt_cache import apply_provider_cache_metadata

ProviderKind = Literal["local", "cloud"]


def cloud_chat_json(
    routing: dict[str, Any],
    *,
    messages: list[dict[str, str]],
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    """OpenAI-compatible ``/chat/completions`` with JSON object response."""
    cloud = mapping_or_empty(routing.get("cloud_runtime"))
    base_url = str(cloud.get("base_url") or "").strip().rstrip("/")
    api_key_env = str(cloud.get("api_key_env") or "OPENAI_API_KEY")
    api_key = env_str(api_key_env)
    if not api_key:
        msg = f"missing API key env {api_key_env}"
        raise ValueError(msg)
    model = str(cloud.get("model_id") or "gpt-4o-mini")
    url = f"{base_url}/chat/completions"
    body = {
        "model": model,
        "messages": apply_provider_cache_metadata(
            messages,
            provider_id="openai",
        ),
        "response_format": {"type": "json_object"},
    }
    resp = httpx.post(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        json=body,
        timeout=timeout_seconds,
    )
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        from agent_core.token_telemetry import (
            TokenTelemetrySample,
            record_token_sample,
            usage_from_provider_response,
        )

        usage = usage_from_provider_response(data)
        record_token_sample(
            TokenTelemetrySample(
                tokens_in=usage.get("tokens_in", 0),
                tokens_out=usage.get("tokens_out", 0),
                cache_read=usage.get("cache_read", 0),
                cache_write=usage.get("cache_write", 0),
                provider="cloud",
            ),
        )
    choices = data.get("choices") if isinstance(data, dict) else None
    if not isinstance(choices, list) or not choices:
        msg = "missing choices in cloud chat response"
        raise ValueError(msg)
    first = choices[0]
    message = first.get("message") if isinstance(first, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        msg = "missing message.content in cloud chat response"
        raise ValueError(msg)
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        msg = "cloud chat JSON mode did not return an object"
        raise TypeError(msg)
    return parsed


def resolve_stage_provider(routing: dict[str, Any], stage_name: str) -> ProviderKind:
    providers = mapping_or_empty(routing.get("stage_providers"))
    raw = providers.get(stage_name)
    if raw is None:
        return "local"
    token = str(raw).strip().lower()
    if token == "cloud" and bool(mapping_or_empty(routing.get("cloud_runtime")).get("enabled")):
        return "cloud"
    return "local"


def probe_cloud_runtime(
    routing: dict[str, Any], *, timeout_seconds: float = 10.0
) -> dict[str, Any]:
    cloud = mapping_or_empty(routing.get("cloud_runtime"))
    if not cloud.get("enabled"):
        return {"enabled": False, "reachable": None, "message": "cloud runtime disabled"}
    base_url = str(cloud.get("base_url") or "").strip().rstrip("/")
    health_path = str(cloud.get("health_path") or "/models").lstrip("/")
    api_key_env = str(cloud.get("api_key_env") or "OPENAI_API_KEY")
    api_key = env_str(api_key_env)
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


def stage_chat_json(
    *,
    repo_root: Path,
    stage_name: str | None,
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    """Route JSON chat to cloud or Ollama based on ``stage_providers`` policy."""
    from orchestrator.routing.chat import ollama_chat_json

    routing = load_model_routing_yaml(repo_root / "configs" / "model-routing.yaml")
    if stage_name and resolve_stage_provider(routing, stage_name) == "cloud":
        return cloud_chat_json(routing, messages=messages, timeout_seconds=timeout_seconds)
    return ollama_chat_json(
        base_url=base_url,
        model=model,
        messages=messages,
        timeout_seconds=timeout_seconds,
    )
