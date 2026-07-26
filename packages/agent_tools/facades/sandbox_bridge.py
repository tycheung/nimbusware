from __future__ import annotations

from broker_client.flags import broker_sandbox_enabled
from broker_client.stage_bind import sandbox_exec_via_broker


def try_broker_sandbox_exec(argv: list[str], cwd: str = ".") -> dict[str, object] | None:
    """Return broker sandbox result when enabled.

    Disabled (``=0``): ``None``.
    Peel (``=1|2``): return result or re-raise on failure (`sak494-d`).
    """
    if not broker_sandbox_enabled():
        return None
    return sandbox_exec_via_broker(argv, cwd=cwd)
