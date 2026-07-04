from __future__ import annotations

from typing import Any

from orchestrator.routing.chat import ollama_chat_json
from orchestrator.routing.manage import ollama_reachable


class OllamaProvider:
    provider_id = "ollama"

    def __init__(self, *, base_url: str | None = None) -> None:
        self._base_url = (base_url or "http://127.0.0.1:11434").rstrip("/")

    @property
    def base_url(self) -> str:
        return self._base_url

    def chat_json(
        self,
        *,
        model_id: str,
        messages: list[dict[str, str]],
        timeout_seconds: float = 120.0,
        cache_blocks: list[dict[str, Any]] | None = None,
        stage_name: str = "",
    ) -> dict[str, Any]:
        return ollama_chat_json(
            base_url=self._base_url,
            model=model_id,
            messages=messages,
            timeout_seconds=timeout_seconds,
        )

    def probe(self, *, timeout_seconds: float = 10.0) -> dict[str, Any]:
        ok = ollama_reachable(self._base_url, timeout_s=timeout_seconds)
        return {
            "ok": ok,
            "message": "Ollama reachable" if ok else "Ollama not reachable",
            "base_url": self._base_url,
        }
