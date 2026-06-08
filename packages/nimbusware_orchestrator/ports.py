"""Narrow ports for LLM-backed roles."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LlmJsonPort(Protocol):
    """Call a chat model returning a JSON object."""

    def complete_json(
        self,
        *,
        model: str,
        system: str,
        user: str,
        timeout_seconds: float,
    ) -> dict[str, Any]: ...
