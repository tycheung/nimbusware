from __future__ import annotations

from typing import Any

from broker_client.client import BrokerClient
from broker_client.flags import broker_tools_enabled, broker_tools_only
from broker_client.mcp_client import BrokerMcpClient
from broker_client.stage_bind.llm import BrokerDisabled


def bind_tools_shell(client: BrokerClient | None = None) -> dict[str, Any]:
    _ = client
    if not broker_tools_enabled():
        raise BrokerDisabled("NIMBUSWARE_BROKER_TOOLS is not enabled")
    return {
        "offer": "tools.shell",
        "steps": ["provision", "bind", "invoke"],
        "transport": "mcp",
        "note": "Use BrokerMcpClient.call_tool('shell_exec', ...) until HTTP admin bind lands",
    }


def shell_exec_via_broker(
    argv: list[str],
    cwd: str = ".",
    *,
    client: BrokerMcpClient | None = None,
) -> dict[str, Any]:
    """Invoke ``shell_exec`` via MCP when the tools dual-run flag is on."""
    if not broker_tools_enabled():
        raise BrokerDisabled("Set NIMBUSWARE_BROKER_TOOLS=1 to route shell through the broker")
    from broker_client.peel_assert import assert_tools_ok, normalize_tool_result

    mcp = client or BrokerMcpClient()
    result = mcp.call_tool("shell_exec", {"argv": argv, "cwd": cwd})
    return assert_tools_ok(  # sak498-g
        normalize_tool_result(result),
        feature="shell_exec",
    )


def try_broker_shell_exec(argv: list[str], cwd: str = ".") -> dict | None:
    """Return broker shell result when enabled; dual-run falls back with ``None``.

    Broker-only (``=2``): re-raise on failure (no local tools fallback) (`sak495-i`).
    """
    if not broker_tools_enabled():
        return None
    try:
        return shell_exec_via_broker(argv, cwd=cwd)
    except Exception:
        if broker_tools_only():  # sak495-i
            raise
        return None
