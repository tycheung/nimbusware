"""Peel stub — local capability removed (sak411–413). Use broker_client / sak offers."""
from __future__ import annotations

_MSG = (
    "{mod} removed by sak411–413 peel; use broker_client stage_bind / "
    "SwissArmyNoife MCP offers instead"
)


def __getattr__(name: str):
    def _gone(*args, **kwargs):
        raise RuntimeError(_MSG.format(mod=__name__ + "." + name))

    _gone.__name__ = name
    _gone.__qualname__ = name
    return _gone
