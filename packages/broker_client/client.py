from __future__ import annotations

from typing import Any

import httpx

from broker_client.http import resolve_base_url, resolve_token
from broker_client.http_get import get_json, post_json


class BrokerClient:
    def __init__(
        self,
        base_url: str | None = None,
        *,
        token: str | None = None,
        timeout: float = 15.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = resolve_base_url(base_url)
        self._token = resolve_token(token)
        self._timeout = timeout
        self._client = client

    @property
    def base_url(self) -> str:
        return self._base_url

    def health(self) -> dict[str, Any]:
        """GET /health; raise on peel error dict (`sak448-i` / `sak486-i`)."""
        from broker_client.peel_assert import assert_capacity_ok

        return assert_capacity_ok(  # sak486-i / sak489-d
            get_json(
                self._base_url,
                "/health",
                token=self._token,
                timeout=self._timeout,
                client=self._client,
            ),
            feature="BrokerClient.health",
        )

    def list_modules(self) -> Any:
        """GET modules list with peel assert (`sak446-g`)."""
        from broker_client.peel_assert import assert_broker_compute_ok

        return assert_broker_compute_ok(  # sak489-d  # sak484-i / sak485-i
            get_json(
                self._base_url,
                "/v1/sak/modules",
                token=self._token,
                timeout=self._timeout,
                client=self._client,
            ),
            feature="list_modules",
            list_key="modules",
        )

    def get_module(self, module_id: str) -> Any:
        """GET module; raise on peel error dict (`sak449-i`)."""
        from broker_client.peel_assert import assert_broker_compute_ok

        return assert_broker_compute_ok(  # sak489-d  # sak485-i
            get_json(
                self._base_url,
                f"/v1/sak/modules/{module_id}",
                token=self._token,
                timeout=self._timeout,
                client=self._client,
            ),
            feature="get_module",
        )

    def capacity(self) -> Any:
        """GET capacity snapshot; raise on peel error dict (`sak449-i` / `sak486-i`)."""
        from broker_client.peel_assert import assert_capacity_ok

        return assert_capacity_ok(  # sak486-i / sak489-d
            get_json(
                self._base_url,
                "/v1/sak/capacity",
                token=self._token,
                timeout=self._timeout,
                client=self._client,
            ),
            feature="capacity",
        )

    def list_work(self) -> Any:
        """GET work list with peel assert (`sak445-f` / `sak488-i`)."""
        from broker_client.peel_assert import assert_broker_compute_ok

        return assert_broker_compute_ok(  # sak489-d  # sak488-i
            get_json(
                self._base_url,
                "/v1/sak/compute/work",
                token=self._token,
                timeout=self._timeout,
                client=self._client,
            ),
            feature="list_work",
            list_key="work",
        )

    def list_nodes(self) -> Any:
        """GET nodes list with peel assert (`sak445-f`)."""
        from broker_client.peel_assert import assert_broker_compute_ok

        return assert_broker_compute_ok(  # sak489-d
            get_json(
                self._base_url,
                "/v1/sak/compute/nodes",
                token=self._token,
                timeout=self._timeout,
                client=self._client,
            ),
            feature="list_nodes",
            list_key="nodes",
        )

    def compute_work(self, payload: dict[str, Any]) -> Any:
        """POST enqueue/claim/complete/get/list (`sak421-e` / `sak447-g`).

        Prefer typed helpers. Hard ``error`` raises except claim empty-polls.
        """
        raw = post_json(
            self._base_url,
            "/v1/sak/compute/work",
            payload,
            token=self._token,
            timeout=self._timeout,
            client=self._client,
        )
        return self._assert_raw_compute_post(raw, payload, feature="compute_work")

    def list_work_filtered(
        self,
        *,
        run_id: str | None = None,
        stage_name: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> Any:
        """POST filtered ``compute_work`` list (`sak424-h` / `sak442-f` / `sak488-i`)."""
        from broker_client.peel_assert import assert_broker_compute_ok
        from broker_client.stage_bind.compute import build_compute_list_payload

        return assert_broker_compute_ok(  # sak489-d  # sak488-i: empty ``[]`` ok; null/miss raises
            self.compute_work(
                build_compute_list_payload(
                    run_id=run_id,
                    stage_name=stage_name,
                    status=status,
                    limit=limit,
                )
            ),
            feature="list_work_filtered",
            list_key="work",
        )

    def compute_nodes(self, payload: dict[str, Any]) -> Any:
        """POST register/heartbeat/list (`sak422-a` / `sak447-g`).

        Prefer typed helpers. Hard ``error`` raises.
        """
        raw = post_json(
            self._base_url,
            "/v1/sak/compute/nodes",
            payload,
            token=self._token,
            timeout=self._timeout,
            client=self._client,
        )
        return self._assert_raw_compute_post(raw, payload, feature="compute_nodes")

    @staticmethod
    def _assert_raw_compute_post(
        raw: Any,
        payload: dict[str, Any],
        *,
        feature: str,
    ) -> Any:
        """Raise on error dicts; allow claim empty-poll errors (`sak447-g`)."""
        from broker_client.peel_assert import is_compute_miss

        if not isinstance(raw, dict):
            return raw
        action = str(payload.get("action") or "")
        if action == "claim":
            return raw
        if is_compute_miss(raw):  # sak483-i / sak487-i / sak489-d
            raise RuntimeError(
                f"broker_miss: {feature}: {raw.get('error') or raw.get('feature') or raw.get('via') or 'miss'!r}"
            )
        if "error" in raw and raw.get("error") is not None:
            raise RuntimeError(f"broker_miss: {feature}: {raw.get('error')!r}")
        return raw

    def list_nodes_filtered(
        self,
        *,
        session_id: str | None = None,
        stale_secs: int | None = None,
    ) -> Any:
        """POST session-scoped ``compute_nodes`` list (`sak424-h` / `sak442-f`)."""
        from broker_client.peel_assert import assert_broker_compute_ok
        from broker_client.stage_bind.compute import build_compute_list_nodes_payload

        return assert_broker_compute_ok(  # sak489-d
            self.compute_nodes(
                build_compute_list_nodes_payload(
                    session_id=session_id,
                    stale_secs=stale_secs,
                )
            ),
            feature="list_nodes_filtered",
            list_key="nodes",
        )

    def register_node(
        self,
        label: str,
        *,
        caps: list[str] | None = None,
        node_id: str | None = None,
        session_id: str | None = None,
    ) -> Any:
        """POST ``compute_nodes`` register (`sak427-f` / `sak438-f`)."""
        from broker_client.peel_assert import assert_broker_compute_record_ok
        from broker_client.stage_bind.compute import build_compute_register_payload

        return assert_broker_compute_record_ok(  # sak489-d  # sak484-i / sak487-i
            self.compute_nodes(
                build_compute_register_payload(
                    label,
                    caps=caps,
                    node_id=node_id,
                    session_id=session_id,
                )
            ),
            feature="BrokerClient.register_node",
            record_key="node",
        )

    def heartbeat_node(self, node_id: str) -> Any:
        """POST ``compute_nodes`` heartbeat (`sak427-f` / `sak438-f`)."""
        from broker_client.peel_assert import assert_broker_compute_record_ok
        from broker_client.stage_bind.compute import build_compute_heartbeat_payload

        return assert_broker_compute_record_ok(  # sak489-d  # sak484-i / sak487-i
            self.compute_nodes(build_compute_heartbeat_payload(node_id)),
            feature="BrokerClient.heartbeat_node",
            record_key="node",
        )

    def enqueue_work(
        self,
        kind: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        """POST ``compute_work`` enqueue (`sak431-h` / `sak438-f`)."""
        from broker_client.peel_assert import assert_broker_compute_record_ok
        from broker_client.stage_bind.compute import build_compute_enqueue_payload

        return assert_broker_compute_record_ok(  # sak489-d  # sak483-i / sak487-i
            self.compute_work(build_compute_enqueue_payload(kind, payload)),
            feature="BrokerClient.enqueue_work",
            record_key="work",
        )

    def claim_work(self, node_id: str) -> Any:
        """POST ``compute_work`` claim (`sak432-e` / `sak438-f` / `sak439-c` / `sak488-i`)."""
        from broker_client.peel_assert import normalize_claim_work_response
        from broker_client.stage_bind.compute import build_compute_claim_payload

        return normalize_claim_work_response(  # sak488-i / sak489-d
            self.compute_work(build_compute_claim_payload(node_id)),
            feature="BrokerClient.claim_work",
        )

    def complete_work(
        self,
        *,
        work_id: str,
        node_id: str,
        result: dict[str, Any] | None = None,
    ) -> Any:
        """POST ``compute_work`` complete (`sak432-e` / `sak438-f`)."""
        from broker_client.peel_assert import assert_broker_compute_record_ok
        from broker_client.stage_bind.compute import build_compute_complete_payload

        return assert_broker_compute_record_ok(  # sak489-d  # sak483-i / sak487-i
            self.compute_work(
                build_compute_complete_payload(
                    work_id=work_id,
                    node_id=node_id,
                    result=dict(result or {}),
                )
            ),
            feature="BrokerClient.complete_work",
            record_key="work",
        )

    def get_work(self, work_id: str) -> Any:
        """POST ``compute_work`` get (`sak432-e` / `sak438-f`)."""
        from broker_client.peel_assert import assert_broker_compute_record_ok
        from broker_client.stage_bind.compute import build_compute_get_payload

        return assert_broker_compute_record_ok(  # sak489-d  # sak483-i / sak487-i
            self.compute_work(build_compute_get_payload(work_id)),
            feature="BrokerClient.get_work",
            record_key="work",
        )

    def requeue_work(self, work_id: str) -> Any:
        """POST ``compute_work`` requeue (`sak429-c`)."""
        from broker_client.peel_assert import assert_broker_compute_record_ok
        from broker_client.stage_bind.compute import build_compute_requeue_payload

        return assert_broker_compute_record_ok(  # sak489-d  # sak483-i / sak487-i
            self.compute_work(build_compute_requeue_payload(work_id)),
            feature="BrokerClient.requeue_work",
            record_key="work",
        )

    def terminate_restart_work(self, work_id: str) -> Any:
        """POST ``compute_work`` requeue as terminate-restart; hard-error assert (`sak448-i`)."""
        from broker_client.stage_bind.compute import terminate_restart_via_broker

        return terminate_restart_via_broker(work_id, http=self)  # sak485-i

    def session_compute_status(
        self,
        session_id: str | None = None,
        *,
        feature: str | None = None,
    ) -> dict[str, Any]:
        """Session nodes + queue depth via shared helper (`sak436-e`)."""
        from compute.broker_session_status import broker_session_compute_status

        return broker_session_compute_status(session_id, feature=feature)  # sak485-i

    def queue_depth(self, session_id: str | None = None) -> dict[str, Any]:
        """Queued work count for a session via broker list (`sak437-f` / `sak480-i` / `sak492-g`)."""
        from broker_client.peel_assert import assert_broker_compute_ok, is_compute_miss
        from broker_client.stage_bind.compute import queue_depth_for_session

        raw = assert_broker_compute_ok(
            self.list_work_filtered(status="queued", limit=200),
            feature="BrokerClient.queue_depth",
            list_key="work",
        )
        if is_compute_miss(raw) or "error" in raw:
            raise RuntimeError(
                f"broker_miss: BrokerClient.queue_depth: "
                f"{raw.get('error') or raw.get('feature') or raw.get('via') or 'miss'!r}"
            )
        items = [w for w in (raw.get("work") or []) if isinstance(w, dict)]
        return {
            "queued": queue_depth_for_session(items, session_id),
            "session_id": session_id,
            "via": "broker",
            "status": "ok",
        }

    def sandbox_exec(
        self,
        argv: list[str],
        cwd: str = ".",
        *,
        mcp: Any = None,
    ) -> dict[str, Any]:
        """MCP ``sandbox_exec`` with domain peel assert (`sak498-g`)."""
        from broker_client.mcp_client import BrokerMcpClient
        from broker_client.peel_assert import assert_sandbox_ok, normalize_tool_result

        client = mcp or BrokerMcpClient()
        return assert_sandbox_ok(
            normalize_tool_result(client.call_tool("sandbox_exec", {"argv": argv, "cwd": cwd})),
            feature="BrokerClient.sandbox_exec",
        )

    def shell_exec(
        self,
        argv: list[str],
        cwd: str = ".",
        *,
        mcp: Any = None,
    ) -> dict[str, Any]:
        """MCP ``shell_exec`` with domain peel assert (`sak498-g`)."""
        from broker_client.mcp_client import BrokerMcpClient
        from broker_client.peel_assert import assert_tools_ok, normalize_tool_result

        client = mcp or BrokerMcpClient()
        return assert_tools_ok(
            normalize_tool_result(client.call_tool("shell_exec", {"argv": argv, "cwd": cwd})),
            feature="BrokerClient.shell_exec",
        )

    def research_fetch(
        self,
        url: str,
        *,
        mcp: Any = None,
    ) -> dict[str, Any]:
        """MCP ``research_fetch`` with domain peel assert (`sak498-g`)."""
        from broker_client.mcp_client import BrokerMcpClient
        from broker_client.peel_assert import assert_research_ok, normalize_tool_result

        client = mcp or BrokerMcpClient()
        return assert_research_ok(
            normalize_tool_result(client.call_tool("research_fetch", {"url": url})),
            feature="BrokerClient.research_fetch",
        )

    def egress_check(
        self,
        url: str,
        *,
        mcp: Any = None,
    ) -> dict[str, Any]:
        """MCP ``egress_check`` with domain peel assert (`sak498-g`)."""
        from broker_client.mcp_client import BrokerMcpClient
        from broker_client.peel_assert import assert_egress_ok, normalize_tool_result

        client = mcp or BrokerMcpClient()
        return assert_egress_ok(
            normalize_tool_result(client.call_tool("egress_check", {"url": url})),
            feature="BrokerClient.egress_check",
        )

    def llm_chat(
        self,
        messages: list[dict[str, Any]],
        *,
        mcp: Any = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """MCP ``llm_chat`` with domain peel assert (`sak498-g`)."""
        from broker_client.mcp_client import BrokerMcpClient
        from broker_client.peel_assert import assert_llm_ok, normalize_tool_result

        client = mcp or BrokerMcpClient()
        arguments: dict[str, Any] = {"messages": messages}
        if model is not None:
            arguments["model"] = model
        return assert_llm_ok(
            normalize_tool_result(client.call_tool("llm_chat", arguments)),
            feature="BrokerClient.llm_chat",
        )
