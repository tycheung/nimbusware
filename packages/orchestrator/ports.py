from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LlmJsonPort(Protocol):
    def complete_json(
        self,
        *,
        model: str,
        system: str,
        user: str,
        timeout_seconds: float,
    ) -> dict[str, Any]: ...
