"""Peel stub — local memory capability removed (sak413). Use memory_bridge / sak."""
from __future__ import annotations


def __getattr__(name: str):
    def _gone(*args, **kwargs):
        raise RuntimeError(
            f"{__name__}.{name} removed (sak413); use agent_tools.memory_bridge / sak memory_*"
        )

    _gone.__name__ = name
    return _gone
