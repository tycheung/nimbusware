from __future__ import annotations

import json
from typing import Any

import httpx

from orchestrator.llm.prompt_cache import apply_provider_cache_metadata
from orchestrator.llm.provider_telemetry import record_provider_chat_telemetry
from orchestrator.provider_registry import probe_api_key_connection


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        provider_id: str,
        base_url: str,
        api_key: str,
        health_path: str = "/models",
    ) -> None:
        self.provider_id = provider_id
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._health_path = health_path

    def chat_json(
        self,
        *,
        model_id: str,
        messages: list[dict[str, str]],
        timeout_seconds: float = 120.0,
        cache_blocks: list[dict[str, Any]] | None = None,
        stage_name: str = "",
    ) -> dict[str, Any]:
        url = f"{self._base_url}/chat/completions"
        cached_messages = apply_provider_cache_metadata(
            messages,
            provider_id=self.provider_id,
            cache_blocks=cache_blocks,
        )
        body = {
            "model": model_id,
            "messages": cached_messages,
            "response_format": {"type": "json_object"},
        }
        resp = httpx.post(
            url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=body,
            timeout=timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json()
        record_provider_chat_telemetry(
            data if isinstance(data, dict) else {},
            provider=self.provider_id,
            stage_name=stage_name,
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

    def probe(self, *, timeout_seconds: float = 10.0) -> dict[str, Any]:
        if not self._api_key:
            return {"ok": False, "message": "API key not set"}
        return probe_api_key_connection(
            base_url=self._base_url,
            api_key=self._api_key,
            health_path=self._health_path,
            timeout_seconds=timeout_seconds,
        )
