from __future__ import annotations

import json
from typing import Any

import httpx


def ollama_chat_json(
    *,
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    """POST ``/api/chat`` with ``format: json``; return parsed JSON object."""
    url = base_url.rstrip("/") + "/api/chat"
    body = {
        "model": model,
        "messages": messages,
        "stream": False,
        "format": "json",
    }
    r = httpx.post(url, json=body, timeout=timeout_seconds)
    r.raise_for_status()
    data = r.json()
    msg = data.get("message") if isinstance(data, dict) else None
    content = msg.get("content") if isinstance(msg, dict) else None
    if not isinstance(content, str):
        msg = "missing message.content in Ollama response"
        raise ValueError(msg)
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        msg = "Ollama JSON mode did not return an object"
        raise TypeError(msg)
    return parsed


def extract_ollama_usage(response: dict[str, Any]) -> dict[str, int]:
    """Extract token/latency hints from a raw Ollama ``/api/chat`` response."""
    out: dict[str, int] = {}
    prompt = response.get("prompt_eval_count")
    completion = response.get("eval_count")
    eval_ns = response.get("eval_duration")
    if isinstance(prompt, int):
        out["prompt_tokens"] = prompt
    if isinstance(completion, int):
        out["completion_tokens"] = completion
    if isinstance(eval_ns, int) and eval_ns > 0:
        out["latency_ms"] = max(1, int(eval_ns / 1_000_000))
    return out


class OllamaLlmJson:
    """Concrete ``LlmJsonPort`` for Ollama."""

    def __init__(self, base_url: str) -> None:
        self._base = base_url.rstrip("/")

    def complete_json(
        self,
        *,
        model: str,
        system: str,
        user: str,
        timeout_seconds: float = 120.0,
    ) -> dict[str, Any]:
        return ollama_chat_json(
            base_url=self._base,
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout_seconds=timeout_seconds,
        )
