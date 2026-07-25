"""Backward-compat shim — see ``agent_tools.facades.slice`` (`refactor:agent_tools-facades`)."""

from agent_tools.facades.slice import (
    SliceImplementResult,
    execute_slice_implement,
    slice_implement_mode,
)

__all__ = [
    "SliceImplementResult",
    "execute_slice_implement",
    "slice_implement_mode",
]
