from __future__ import annotations

from typing import Any


def __getattr__(name: str):
    def _gone(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(
            f"orchestrator.provider_routing_facade.{name} removed (sak411); "
            "use broker_client / sak llm.resolve"
        )

    return _gone
