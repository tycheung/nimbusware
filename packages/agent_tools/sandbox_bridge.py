"""Sandbox broker edge (+ peel stubs for deleted sandbox.py symbols)."""
from __future__ import annotations

from typing import Any

from agent_tools.facades.sandbox_bridge import try_broker_sandbox_exec

__all__ = [
    "try_broker_sandbox_exec",
    "raise_sandbox_peel_miss",
    "raise_tools_peel_miss",
    "resolve_sandbox_backend",
    "run_subprocess_in_sandbox",
    "docker_cli_available",
]


def raise_sandbox_peel_miss(feature: str = "shell") -> None:
    """Back-compat delegate to ``agent_tools.broker_route`` (`sak495-i` / `sak496-d`)."""
    from agent_tools.broker_route import raise_sandbox_peel_miss as _raise

    _raise(feature)


def raise_tools_peel_miss(feature: str = "shell") -> None:
    """Back-compat delegate to ``agent_tools.broker_route`` (`sak495-i` / `sak496-d`)."""
    from agent_tools.broker_route import raise_tools_peel_miss as _raise

    _raise(feature)


def resolve_sandbox_backend(*args: Any, **kwargs: Any) -> str:
    return "broker"


def run_subprocess_in_sandbox(*args: Any, **kwargs: Any) -> Any:
    raise RuntimeError(
        "agent_tools.sandbox local backends removed (sak412); use try_broker_sandbox_exec"
    )


def docker_cli_available() -> bool:
    return False
