from __future__ import annotations

from typing import Any

from broker_client.client import BrokerClient
from broker_client.flags import broker_sandbox_enabled
from broker_client.mcp_client import BrokerMcpClient
from broker_client.stage_bind.llm import BrokerDisabled


def bind_sandbox_exec(client: BrokerClient | None = None) -> dict[str, Any]:
    _ = client
    if not broker_sandbox_enabled():
        raise BrokerDisabled("NIMBUSWARE_BROKER_SANDBOX is not enabled")
    return {
        "offer": "sandbox.exec",
        "steps": ["provision", "bind", "invoke"],
        "transport": "mcp",
        "note": "Use BrokerMcpClient.call_tool('sandbox_exec', ...) until HTTP admin bind lands",
    }


def sandbox_exec_via_broker(
    argv: list[str],
    cwd: str = ".",
    *,
    client: BrokerMcpClient | None = None,
) -> dict[str, Any]:
    """Invoke ``sandbox_exec`` via MCP when the sandbox dual-run flag is on."""
    if not broker_sandbox_enabled():
        raise BrokerDisabled("Set NIMBUSWARE_BROKER_SANDBOX=1 to route sandbox through the broker")
    from broker_client.peel_assert import assert_sandbox_ok, normalize_tool_result

    mcp = client or BrokerMcpClient()
    result = mcp.call_tool("sandbox_exec", {"argv": argv, "cwd": cwd})
    return assert_sandbox_ok(  # sak498-g
        normalize_tool_result(result),
        feature="sandbox_exec",
    )
