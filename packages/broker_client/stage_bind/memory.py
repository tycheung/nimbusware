from __future__ import annotations

from typing import Any

from broker_client.client import BrokerClient
from broker_client.flags import broker_memory_enabled
from broker_client.mcp_client import BrokerMcpClient
from broker_client.stage_bind.llm import BrokerDisabled


def bind_memory_search(client: BrokerClient | None = None) -> dict[str, Any]:
    _ = client
    if not broker_memory_enabled():
        raise BrokerDisabled("NIMBUSWARE_BROKER_MEMORY is not enabled")
    return {
        "offer": "memory.search",
        "steps": ["provision", "bind", "invoke"],
        "transport": "mcp",
        "note": "Use BrokerMcpClient.call_tool('memory_search', ...) until HTTP admin bind lands",
    }


def memory_search_via_broker(
    query: str,
    *,
    client: BrokerMcpClient | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Invoke ``memory_search`` via MCP when the memory dual-run flag is on."""
    if not broker_memory_enabled():
        raise BrokerDisabled("Set NIMBUSWARE_BROKER_MEMORY=1 to route memory through the broker")
    mcp = client or BrokerMcpClient()
    arguments: dict[str, Any] = {"query": query}
    if limit is not None:
        arguments["limit"] = limit
    from broker_client.peel_assert import assert_memory_ok, normalize_tool_result

    result = mcp.call_tool("memory_search", arguments)
    return assert_memory_ok(  # sak495-g / sak498-g
        normalize_tool_result(result),
        feature="memory_search",
    )
