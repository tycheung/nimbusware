"""Peel stub — local memory capability removed (sak413). Use memory_bridge / sak."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def __getattr__(name: str) -> Callable[..., Any]:
    def _gone(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(
            f"{__name__}.{name} removed (sak413); use agent_tools.memory_bridge / sak memory_*"
        )

    _gone.__name__ = name
    return _gone
