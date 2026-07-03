from __future__ import annotations

from typing import Any


def scan_tools_failed(
    tool_summary: dict[str, Any],
    tool_names: tuple[str, ...],
    *,
    tools_key: str = "security_scan_tools",
) -> tuple[bool, list[str]]:
    tools = tool_summary.get(tools_key)
    if not isinstance(tools, dict):
        return False, []
    failing: list[str] = []
    for name in tool_names:
        try:
            code = int(tools.get(name, 0))
        except (TypeError, ValueError):
            code = 0
        if code != 0:
            failing.append(name)
    return bool(failing), failing
