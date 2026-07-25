from __future__ import annotations

from typing import Any

from broker_client.client import BrokerClient
from broker_client.flags import broker_egress_enabled, broker_research_enabled
from broker_client.mcp_client import BrokerMcpClient
from broker_client.stage_bind.llm import BrokerDisabled


def bind_research_fetch(client: BrokerClient | None = None) -> dict[str, Any]:
    _ = client
    if not broker_research_enabled():
        raise BrokerDisabled("NIMBUSWARE_BROKER_RESEARCH is not enabled")
    return {
        "offer": "research.fetch",
        "steps": ["provision", "bind", "invoke"],
        "transport": "mcp",
        "note": "Use BrokerMcpClient.call_tool('research_fetch', ...) until HTTP admin bind lands",
    }


def research_fetch_via_broker(
    url: str,
    *,
    client: BrokerMcpClient | None = None,
) -> dict[str, Any]:
    """Invoke ``research_fetch`` via MCP when the research dual-run flag is on."""
    if not broker_research_enabled():
        raise BrokerDisabled("Set NIMBUSWARE_BROKER_RESEARCH=1 to route research through the broker")
    from broker_client.peel_assert import assert_research_ok, normalize_tool_result

    mcp = client or BrokerMcpClient()
    result = mcp.call_tool("research_fetch", {"url": url})
    return assert_research_ok(  # sak498-g
        normalize_tool_result(result),
        feature="research_fetch",
    )


def bind_egress_check(client: BrokerClient | None = None) -> dict[str, Any]:
    _ = client
    if not broker_egress_enabled():
        raise BrokerDisabled("NIMBUSWARE_BROKER_EGRESS is not enabled")
    return {
        "offer": "network.egress.check",
        "steps": ["provision", "bind", "invoke"],
        "transport": "mcp",
        "note": "Use BrokerMcpClient.call_tool('egress_check', ...) until HTTP admin bind lands",
    }


def egress_check_via_broker(
    url: str,
    *,
    client: BrokerMcpClient | None = None,
) -> dict[str, Any]:
    """Invoke ``egress_check`` via MCP when the egress dual-run flag is on."""
    if not broker_egress_enabled():
        raise BrokerDisabled("Set NIMBUSWARE_BROKER_EGRESS=1 to route egress through the broker")
    from broker_client.peel_assert import assert_egress_ok, normalize_tool_result

    mcp = client or BrokerMcpClient()
    result = mcp.call_tool("egress_check", {"url": url})
    return assert_egress_ok(  # sak498-g
        normalize_tool_result(result),
        feature="egress_check",
    )
