from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LlmProvider(Protocol):
    provider_id: str

    def chat_json(
        self,
        *,
        model_id: str,
        messages: list[dict[str, str]],
        timeout_seconds: float = 120.0,
    ) -> dict[str, Any]: ...

    def probe(self, *, timeout_seconds: float = 10.0) -> dict[str, Any]: ...
