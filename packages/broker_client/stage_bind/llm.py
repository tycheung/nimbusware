from __future__ import annotations

from typing import Any

from broker_client.client import BrokerClient
from broker_client.flags import broker_llm_enabled
from broker_client.mcp_client import BrokerMcpClient


class BrokerDisabled(Exception):
    """Raised when a broker-backed path is requested but the domain flag is off."""


def bind_llm_chat(client: BrokerClient | None = None) -> dict[str, Any]:
    _ = client
    if not broker_llm_enabled():
        raise BrokerDisabled("NIMBUSWARE_BROKER_LLM is not enabled")
    return {
        "offer": "llm.chat",
        "steps": ["provision", "bind", "invoke"],
        "transport": "mcp",
        "note": "Use BrokerMcpClient.call_tool('llm_chat', ...) until HTTP admin bind lands",
    }


def llm_chat_via_broker(
    messages: list[dict[str, Any]],
    *,
    client: BrokerMcpClient | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Invoke ``llm_chat`` via MCP when the LLM dual-run flag is on."""
    import os

    if not broker_llm_enabled():
        raise BrokerDisabled("Set NIMBUSWARE_BROKER_LLM=1 to route LLM through the broker")
    mcp = client or BrokerMcpClient()
    resolved_model = (model or os.environ.get("NIMBUSWARE_BROKER_LLM_MODEL") or "").strip() or "echo"
    arguments: dict[str, Any] = {"messages": messages, "model": resolved_model}
    from broker_client.peel_assert import assert_llm_ok, normalize_tool_result

    result = mcp.call_offer_tool("llm_chat", "llm.chat", arguments)
    return assert_llm_ok(  # sak498-g
        normalize_tool_result(result),
        feature="llm_chat",
    )
