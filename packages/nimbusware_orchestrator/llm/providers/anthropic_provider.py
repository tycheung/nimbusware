from __future__ import annotations

import json
from typing import Any

import httpx

from nimbusware_orchestrator.provider_registry import probe_anthropic_connection

_ANTHROPIC_VERSION = "2023-06-01"
_JSON_SYSTEM = "Respond with a single valid JSON object only. No markdown fences or prose."


class AnthropicProvider:
    def __init__(
        self,
        *,
        provider_id: str = "anthropic",
        base_url: str,
        api_key: str,
    ) -> None:
        self.provider_id = provider_id
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def chat_json(
        self,
        *,
        model_id: str,
        messages: list[dict[str, str]],
        timeout_seconds: float = 120.0,
    ) -> dict[str, Any]:
        system_parts: list[str] = [_JSON_SYSTEM]
        api_messages: list[dict[str, str]] = []
        for row in messages:
            role = str(row.get("role") or "user")
            content = str(row.get("content") or "")
            if role == "system":
                if content.strip():
                    system_parts.append(content.strip())
                continue
            api_role = "assistant" if role == "assistant" else "user"
            api_messages.append({"role": api_role, "content": content})
        if not api_messages:
            api_messages = [{"role": "user", "content": "Respond with JSON."}]
        body: dict[str, Any] = {
            "model": model_id,
            "max_tokens": 8192,
            "system": "\n\n".join(system_parts),
            "messages": api_messages,
        }
        resp = httpx.post(
            f"{self._base_url}/v1/messages",
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json=body,
            timeout=timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            msg = "invalid anthropic response"
            raise ValueError(msg)
        content_blocks = data.get("content")
        if not isinstance(content_blocks, list) or not content_blocks:
            msg = "missing content in anthropic response"
            raise ValueError(msg)
        text_parts: list[str] = []
        for block in content_blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(str(block.get("text") or ""))
        content = "".join(text_parts).strip()
        if not content:
            msg = "empty text in anthropic response"
            raise ValueError(msg)
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            msg = "anthropic JSON mode did not return an object"
            raise TypeError(msg)
        return parsed

    def probe(self, *, timeout_seconds: float = 10.0) -> dict[str, Any]:
        if not self._api_key:
            return {"ok": False, "message": "API key not set"}
        return probe_anthropic_connection(
            base_url=self._base_url,
            api_key=self._api_key,
            timeout_seconds=timeout_seconds,
        )
