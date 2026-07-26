"""Filesystem jail stub after sak412 filesystem_jail.py delete."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def default_jail_policy(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {"mode": "broker", "removed": "sak412"}


def assert_rel_allowed(rel: str, *args: Any, **kwargs: Any) -> None:
    if ".." in rel.replace("\\", "/").split("/"):
        raise ValueError(f"path not allowed: {rel!r}")


def __getattr__(name: str) -> Callable[..., Any]:
    def _gone(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(
            f"agent_tools.filesystem_jail.{name} removed (sak412); use sak sandbox jail"
        )

    return _gone
