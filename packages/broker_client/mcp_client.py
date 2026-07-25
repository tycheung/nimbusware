"""Streamable HTTP MCP client for SwissArmyNoife (`sak402-a` / `sak402-b`).

Posts JSON-RPC to the MCP endpoint. ``initialize`` negotiates session (header or body);
``call_tool`` / ``list_tools`` ensure session once per client instance.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from broker_client.http import normalize_base_url, resolve_token
from broker_client.mcp_rpc import (
    body_from_response,
    initialize_params,
    parse_rpc_result,
    post_json_rpc,
    session_from_response,
)

_DEFAULT_MCP_URL = "http://127.0.0.1:8080/mcp"
_BROKER_MCP_ENV = "NIMBUSWARE_BROKER_MCP"


def resolve_mcp_url(base_url: str | None = None) -> str:
    raw = base_url if base_url is not None else os.environ.get(_BROKER_MCP_ENV, _DEFAULT_MCP_URL)
    return normalize_base_url(raw)


def mcp_configured() -> bool:
    return bool(os.environ.get(_BROKER_MCP_ENV, "").strip())


class BrokerMcpClient:
    """MCP client over Streamable HTTP with lazy ``initialize`` session."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        token: str | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = resolve_mcp_url(base_url)
        self._token = resolve_token(token)
        self._timeout = timeout
        self._client = client
        self._rpc_id = 0
        self._session_id: str | None = None
        self._initialized = False
        self._offer_bindings: dict[str, str] = {}

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def session_id(self) -> str | None:
        return self._session_id

    def ensure_offer_binding(self, offer_id: str) -> str:
        """``session_bind`` one offer and cache ``binding_id`` for offer tools."""
        cached = self._offer_bindings.get(offer_id)
        if cached:
            return cached
        from broker_client.peel_assert import normalize_tool_result

        raw = self.call_tool("session_bind", {"offer_ids": [offer_id]})
        normalized = normalize_tool_result(raw)
        bindings = normalized.get("bindings")
        if not isinstance(bindings, list):
            raise RuntimeError(f"session_bind missing bindings for {offer_id!r}: {normalized!r}")
        for row in bindings:
            if not isinstance(row, dict):
                continue
            oid = str(row.get("offer_id") or "")
            bid = str(row.get("binding_id") or "").strip()
            if oid and bid:
                self._offer_bindings[oid] = bid
        binding_id = self._offer_bindings.get(offer_id)
        if not binding_id:
            raise RuntimeError(f"session_bind did not return binding for {offer_id!r}")
        return binding_id

    def call_offer_tool(
        self,
        name: str,
        offer_id: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Call an offer tool after ensuring a ``binding_id`` is present."""
        args = dict(arguments or {})
        if "binding_id" not in args:
            args["binding_id"] = self.ensure_offer_binding(offer_id)
        return self.call_tool(name, args)

    def _next_id(self) -> int:
        self._rpc_id += 1
        return self._rpc_id

    def _post_raw(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        return post_json_rpc(
            self._base_url,
            method=method,
            params=params,
            rpc_id=self._next_id(),
            token=self._token,
            session_id=self._session_id,
            timeout=self._timeout,
            client=self._client,
        )

    def _post_rpc(self, method: str, params: dict[str, Any] | None = None) -> Any:
        return body_from_response(self._post_raw(method, params))

    def initialize(self) -> Any:
        """Post MCP ``initialize``; capture ``mcp-session-id`` from header or body."""
        response = self._post_raw("initialize", initialize_params())
        sid = session_from_response(response)
        if sid:
            self._session_id = sid
        # Streamable HTTP requires initialized notification before tools/* (202 Accepted).
        post_json_rpc(
            self._base_url,
            method="notifications/initialized",
            params=None,
            rpc_id=0,
            token=self._token,
            session_id=self._session_id,
            timeout=self._timeout,
            client=self._client,
            notification=True,
        )
        self._initialized = True
        body = body_from_response(response)
        return parse_rpc_result(body, operation="initialize")

    def ensure_session(self) -> None:
        if not self._initialized:
            self.initialize()

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        self.ensure_session()
        body = self._post_rpc(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
        )
        return parse_rpc_result(body, operation="tools/call")

    def list_tools(self) -> Any:
        self.ensure_session()
        body = self._post_rpc("tools/list")
        return parse_rpc_result(body, operation="tools/list")

    def tools_list(self) -> Any:
        """Alias for ``list_tools`` (MCP ``tools/list`` JSON-RPC)."""
        return self.list_tools()

    def ping(self) -> Any:
        return self.call_tool("ping")
